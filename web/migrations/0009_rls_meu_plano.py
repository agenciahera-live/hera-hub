"""Segurança no banco para o Meu plano (passo 3.6).

O plano e os objetivos são do criador: só ele grava (e a rotina diária, como sistema, para os lembretes e para a
LGPD). A gestão lê (decisão da Mariana de 19/11/2026: a gestão vê o plano), mas nunca edita. Um criador nunca lê
o plano de outro."""
from django.db import migrations

TABLES = ["engage_creatorplan", "engage_creatorgoal"]


def forward():
    sql = ""
    for t in TABLES:
        wr = "(hera_is_own(creator_id) OR hera_is_system())"
        # apagar também pode a sócia, porque o Django apaga plano e objetivos junto quando ela exclui um criador
        dl = ("(hera_is_own(creator_id) OR hera_is_system() OR EXISTS (SELECT 1 FROM crm_creator c "
              "WHERE c.id = creator_id AND hera_has_role(c.agency_id, ARRAY['admin'])))")
        sql += f"""
ALTER TABLE {t} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {t} FORCE ROW LEVEL SECURITY;
CREATE POLICY {t}_select ON {t} FOR SELECT USING (hera_can_view(creator_id));
CREATE POLICY {t}_insert ON {t} FOR INSERT WITH CHECK {wr};
CREATE POLICY {t}_update ON {t} FOR UPDATE USING {wr} WITH CHECK {wr};
CREATE POLICY {t}_delete ON {t} FOR DELETE USING {dl};
"""
    return sql


def reverse():
    sql = ""
    for t in TABLES:
        for op in ("select", "insert", "update", "delete"):
            sql += f"DROP POLICY IF EXISTS {t}_{op} ON {t};\n"
        sql += f"ALTER TABLE {t} DISABLE ROW LEVEL SECURITY;\n"
    return sql


class Migration(migrations.Migration):
    dependencies = [("web", "0008_rls_campanha_do_momento"), ("engage", "0024_meu_plano")]
    operations = [migrations.RunSQL(forward(), reverse())]
