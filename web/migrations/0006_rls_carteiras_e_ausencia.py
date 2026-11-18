"""Segurança no banco para a ausência da gestora ("Hoje não trabalho") e para quem cobre a carteira dela.

1. crm_absence: leem as sócias, a própria gestora e quem cobre. A gestora só marca a própria ausência, só para hoje,
   e só com quem as sócias definiram para cobri-la (ou sem ninguém, que quer dizer "as sócias"). Depois, só pode cancelar.
   Assim, quem decide quem enxerga uma carteira são sempre as sócias.
2. hera_covers: quem cobre enxerga a carteira da gestora ausente SÓ no dia da ausência, e só enquanto tiver o papel
   de sócia ou de recrutadora. No dia seguinte (ou se a ausência for cancelada) o acesso some sozinho.
3. Quem cobre só registra o contato: "Enviei" (crm_contact), "Respondeu" (crm_reply, crm_contact, crm_cadencestate)
   e nota (crm_note). Não edita cadastro, não registra saída e não lê o código de acesso ao app.
"""
from django.db import migrations

FORWARD = r"""
-- Dia de trabalho (Brasília). O app usa o mesmo dia em crm/absence.py (timezone.localdate).
CREATE OR REPLACE FUNCTION hera_today() RETURNS date LANGUAGE sql STABLE AS $$
  SELECT (now() AT TIME ZONE 'America/Sao_Paulo')::date $$;

CREATE OR REPLACE FUNCTION hera_default_cover(mgr bigint, ag bigint) RETURNS bigint LANGUAGE sql STABLE AS $$
  SELECT m.covered_by_id FROM core_membership m
  WHERE m.user_id = mgr AND m.agency_id = ag AND m.role = 'gestora' AND m.active $$;

ALTER TABLE crm_absence ENABLE ROW LEVEL SECURITY;
ALTER TABLE crm_absence FORCE ROW LEVEL SECURITY;
CREATE POLICY crm_absence_select ON crm_absence FOR SELECT USING (
  hera_is_system() OR hera_has_role(agency_id, ARRAY['admin']) OR manager_id = hera_uid() OR cover_id = hera_uid());
CREATE POLICY crm_absence_insert ON crm_absence FOR INSERT WITH CHECK (
  hera_is_system() OR hera_has_role(agency_id, ARRAY['admin'])
  OR (manager_id = hera_uid() AND hera_has_role(agency_id, ARRAY['gestora']) AND day = hera_today()
      AND (cover_id IS NULL OR cover_id = hera_default_cover(manager_id, agency_id))));
CREATE POLICY crm_absence_update ON crm_absence FOR UPDATE
  USING (hera_is_system() OR hera_has_role(agency_id, ARRAY['admin']) OR manager_id = hera_uid())
  WITH CHECK (hera_is_system() OR hera_has_role(agency_id, ARRAY['admin'])
              OR (manager_id = hera_uid() AND cancelled_at IS NOT NULL));
CREATE POLICY crm_absence_delete ON crm_absence FOR DELETE USING (
  hera_is_system() OR hera_has_role(agency_id, ARRAY['admin']));

-- Quem cobre hoje a gestora que cuida deste criador.
CREATE OR REPLACE FUNCTION hera_covers(cid bigint, ag bigint) RETURNS boolean LANGUAGE sql STABLE AS $$
  SELECT EXISTS (
    SELECT 1 FROM crm_absence a
    JOIN crm_portfolioassignment p ON p.manager_id = a.manager_id AND p.valid_to IS NULL
    WHERE p.creator_id = cid AND a.agency_id = ag AND a.cover_id = hera_uid()
      AND a.cancelled_at IS NULL AND a.day = hera_today()
      AND hera_has_role(ag, ARRAY['admin','recrutadora'])) $$;

-- Igual à função de web/0001, com a cobertura no fim.
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
              AND m.active AND m.role = 'gestor_parceira' AND m.partner_group_id = pg))
      OR hera_covers(cid, ag) $$;

-- Registrar contato: quem edita o criador ou quem cobre a carteira dele hoje.
CREATE OR REPLACE FUNCTION hera_staff_can_contact(cid bigint) RETURNS boolean LANGUAGE sql STABLE AS $$
  SELECT EXISTS (SELECT 1 FROM crm_creator c WHERE c.id = cid
                 AND (hera_staff_edits(c.id, c.agency_id) OR hera_covers(c.id, c.agency_id))) $$;

ALTER POLICY crm_contact_insert ON crm_contact WITH CHECK (hera_staff_can_contact(creator_id));
ALTER POLICY crm_contact_update ON crm_contact USING (hera_staff_can_contact(creator_id)) WITH CHECK (hera_staff_can_contact(creator_id));
ALTER POLICY crm_reply_insert ON crm_reply WITH CHECK (hera_staff_can_contact(creator_id));
ALTER POLICY crm_note_insert ON crm_note WITH CHECK (hera_staff_can_contact(creator_id));
ALTER POLICY crm_cadencestate_update ON crm_cadencestate USING (hera_staff_can_contact(creator_id)) WITH CHECK (hera_staff_can_contact(creator_id));
"""

REVERSE = r"""
ALTER POLICY crm_contact_insert ON crm_contact WITH CHECK (hera_staff_can_edit(creator_id));
ALTER POLICY crm_contact_update ON crm_contact USING (hera_staff_can_edit(creator_id)) WITH CHECK (hera_staff_can_edit(creator_id));
ALTER POLICY crm_reply_insert ON crm_reply WITH CHECK (hera_staff_can_edit(creator_id));
ALTER POLICY crm_note_insert ON crm_note WITH CHECK (hera_staff_can_edit(creator_id));
ALTER POLICY crm_cadencestate_update ON crm_cadencestate USING (hera_staff_can_edit(creator_id)) WITH CHECK (hera_staff_can_edit(creator_id));
DROP FUNCTION IF EXISTS hera_staff_can_contact(bigint);

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
DROP FUNCTION IF EXISTS hera_covers(bigint, bigint);

DROP POLICY IF EXISTS crm_absence_select ON crm_absence;
DROP POLICY IF EXISTS crm_absence_insert ON crm_absence;
DROP POLICY IF EXISTS crm_absence_update ON crm_absence;
DROP POLICY IF EXISTS crm_absence_delete ON crm_absence;
ALTER TABLE crm_absence DISABLE ROW LEVEL SECURITY;
DROP FUNCTION IF EXISTS hera_default_cover(bigint, bigint);
DROP FUNCTION IF EXISTS hera_today();
"""


class Migration(migrations.Migration):
    dependencies = [("web", "0005_rls_restricao_e_visita"), ("crm", "0009_carteiras_e_ausencia"), ("core", "0010_carteiras_e_ausencia")]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
