"""Segurança no banco: Row-Level Security (RLS).

Regras:
- `app.user_id` = usuário da requisição (definido pelo middleware).
- `app.system = on` = tarefas internas (importação por comando, cron, seeds).
- Streamer vê só o creator ligado ao seu usuário.
- Admin, Analista e Financeiro veem todos os creators da agência.
- Gestora vê só a carteira vigente; Recrutadora, quem recrutou; Gestor de parceira, o próprio grupo.
- Tabelas internas (notas, tags, 1:1, contatos...) nunca são visíveis ao streamer.
- FORCE ROW LEVEL SECURITY: vale também para o dono das tabelas.
  O usuário de banco do app NÃO pode ser superusuário nem ter BYPASSRLS.
"""
from django.db import migrations

FUNCTIONS = r"""
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE OR REPLACE FUNCTION hera_uid() RETURNS bigint LANGUAGE sql STABLE AS $$
  SELECT NULLIF(current_setting('app.user_id', true), '')::bigint $$;

CREATE OR REPLACE FUNCTION hera_is_system() RETURNS boolean LANGUAGE sql STABLE AS $$
  SELECT coalesce(current_setting('app.system', true), '') = 'on' $$;

CREATE OR REPLACE FUNCTION hera_has_role(ag bigint, roles text[]) RETURNS boolean LANGUAGE sql STABLE AS $$
  SELECT EXISTS (SELECT 1 FROM core_membership m
                 WHERE m.user_id = hera_uid() AND m.agency_id = ag AND m.active AND m.role = ANY(roles)) $$;

CREATE OR REPLACE FUNCTION hera_staff_sees(cid bigint, ag bigint, recruiter bigint, pg bigint) RETURNS boolean
LANGUAGE sql STABLE AS $$
  SELECT hera_is_system()
      OR hera_has_role(ag, ARRAY['admin','analista','financeiro'])
      OR (hera_has_role(ag, ARRAY['gestora']) AND EXISTS (
            SELECT 1 FROM crm_portfolioassignment p
            WHERE p.creator_id = cid AND p.manager_id = hera_uid() AND p.valid_to IS NULL))
      OR (hera_has_role(ag, ARRAY['recrutadora']) AND recruiter = hera_uid())
      OR (pg IS NOT NULL AND EXISTS (
            SELECT 1 FROM core_membership m WHERE m.user_id = hera_uid() AND m.agency_id = ag
              AND m.active AND m.role = 'gestor_parceira' AND m.partner_group_id = pg)) $$;

CREATE OR REPLACE FUNCTION hera_staff_edits(cid bigint, ag bigint) RETURNS boolean LANGUAGE sql STABLE AS $$
  SELECT hera_is_system()
      OR hera_has_role(ag, ARRAY['admin'])
      OR (hera_has_role(ag, ARRAY['gestora']) AND EXISTS (
            SELECT 1 FROM crm_portfolioassignment p
            WHERE p.creator_id = cid AND p.manager_id = hera_uid() AND p.valid_to IS NULL)) $$;

-- As funções abaixo consultam crm_creator COM o RLS dele aplicado.
CREATE OR REPLACE FUNCTION hera_can_view(cid bigint) RETURNS boolean LANGUAGE sql STABLE AS $$
  SELECT EXISTS (SELECT 1 FROM crm_creator c WHERE c.id = cid) $$;

CREATE OR REPLACE FUNCTION hera_staff_can_view(cid bigint) RETURNS boolean LANGUAGE sql STABLE AS $$
  SELECT EXISTS (SELECT 1 FROM crm_creator c WHERE c.id = cid
                 AND hera_staff_sees(c.id, c.agency_id, c.recruited_by_id, c.partner_group_id)) $$;

CREATE OR REPLACE FUNCTION hera_staff_can_edit(cid bigint) RETURNS boolean LANGUAGE sql STABLE AS $$
  SELECT EXISTS (SELECT 1 FROM crm_creator c WHERE c.id = cid AND hera_staff_edits(c.id, c.agency_id)) $$;

CREATE OR REPLACE FUNCTION hera_is_own(cid bigint) RETURNS boolean LANGUAGE sql STABLE AS $$
  SELECT EXISTS (SELECT 1 FROM crm_creator c WHERE c.id = cid AND c.user_id = hera_uid()) $$;
"""

CREATOR = r"""
ALTER TABLE crm_creator ENABLE ROW LEVEL SECURITY;
ALTER TABLE crm_creator FORCE ROW LEVEL SECURITY;
CREATE POLICY creator_select ON crm_creator FOR SELECT
  USING (user_id = hera_uid() OR hera_staff_sees(id, agency_id, recruited_by_id, partner_group_id));
CREATE POLICY creator_insert ON crm_creator FOR INSERT
  WITH CHECK (hera_is_system() OR hera_has_role(agency_id, ARRAY['admin']));
CREATE POLICY creator_update ON crm_creator FOR UPDATE
  USING (user_id = hera_uid() OR hera_staff_edits(id, agency_id))
  WITH CHECK (user_id = hera_uid() OR hera_staff_edits(id, agency_id));
CREATE POLICY creator_delete ON crm_creator FOR DELETE
  USING (hera_is_system() OR hera_has_role(agency_id, ARRAY['admin']));
"""

# Tabelas por creator que o próprio streamer pode ler.
SHARED = [
    "crm_creatorprivate", "crm_creatorusername", "crm_goal",
    "data_creatorsnapshot", "data_monthlyresult", "data_creatorgrouphistory",
    "engage_campaignparticipant", "engage_pointsledger",
]
# Tabelas por creator em que o próprio streamer também escreve.
STREAMER_WRITES = ["engage_lessonprogress", "engage_battlerequest", "engage_supportticket"]
# Tabelas internas: nunca visíveis ao streamer.
INTERNAL = [
    "crm_creatortag", "crm_note", "crm_oneonone", "crm_actionitem", "crm_contact",
    "crm_cadencestate", "crm_creatoronboarding", "crm_exitrecord", "crm_alertdismissal",
    "data_taskresult",
]


def child_sql(table, mode):
    sel = {
        "shared": "hera_can_view(creator_id)",
        "writes": "hera_can_view(creator_id)",
        "internal": "hera_staff_can_view(creator_id)",
    }[mode]
    wr = "hera_staff_can_edit(creator_id)"
    if mode == "writes" or table == "crm_creatorprivate":
        wr = "(hera_staff_can_edit(creator_id) OR hera_is_own(creator_id))"
    return f"""
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
CREATE POLICY {table}_select ON {table} FOR SELECT USING ({sel});
CREATE POLICY {table}_insert ON {table} FOR INSERT WITH CHECK ({wr});
CREATE POLICY {table}_update ON {table} FOR UPDATE USING ({wr}) WITH CHECK ({wr});
CREATE POLICY {table}_delete ON {table} FOR DELETE USING ({wr});
"""


OTHER = r"""
ALTER TABLE data_importrow ENABLE ROW LEVEL SECURITY;
ALTER TABLE data_importrow FORCE ROW LEVEL SECURITY;
CREATE POLICY importrow_all ON data_importrow FOR ALL
  USING (EXISTS (SELECT 1 FROM data_importbatch b WHERE b.id = batch_id
                 AND (hera_is_system() OR hera_has_role(b.agency_id, ARRAY['admin','financeiro']))))
  WITH CHECK (EXISTS (SELECT 1 FROM data_importbatch b WHERE b.id = batch_id
                 AND (hera_is_system() OR hera_has_role(b.agency_id, ARRAY['admin','financeiro']))));

ALTER TABLE engage_notification ENABLE ROW LEVEL SECURITY;
ALTER TABLE engage_notification FORCE ROW LEVEL SECURITY;
CREATE POLICY notif_select ON engage_notification FOR SELECT USING (user_id = hera_uid() OR hera_is_system());
CREATE POLICY notif_update ON engage_notification FOR UPDATE USING (user_id = hera_uid() OR hera_is_system());
CREATE POLICY notif_insert ON engage_notification FOR INSERT WITH CHECK (true);
CREATE POLICY notif_delete ON engage_notification FOR DELETE USING (user_id = hera_uid() OR hera_is_system());
"""


def forward_sql():
    parts = [FUNCTIONS, CREATOR]
    parts += [child_sql(t, "shared") for t in SHARED]
    parts += [child_sql(t, "writes") for t in STREAMER_WRITES]
    parts += [child_sql(t, "internal") for t in INTERNAL]
    parts.append(OTHER)
    return "\n".join(parts)


def reverse_sql():
    tables = ["crm_creator", "data_importrow", "engage_notification"] + SHARED + STREAMER_WRITES + INTERNAL
    return "\n".join(f"ALTER TABLE {t} DISABLE ROW LEVEL SECURITY;" for t in tables)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
        ("crm", "0001_initial"),
        ("data", "0001_initial"),
        ("engage", "0001_initial"),
    ]
    operations = [migrations.RunSQL(forward_sql(), reverse_sql())]
