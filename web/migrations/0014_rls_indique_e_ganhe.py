"""Segurança no banco para o Indique e ganhe (passo 4.7).

- crm_referral (a indicação e a situação): lê quem enxerga a pessoa indicada ou quem indicou na gestão, e o próprio
  criador que indicou (só a situação; os números da pessoa indicada ficam nas tabelas dela, que ele não lê). A pessoa
  indicada não lê. Só o sistema (o registro pela ficha roda como sistema, dentro do serviço) e as sócias gravam.
- crm_referralbonus (os valores): o criador que indicou lê os dele; as sócias e o financeiro leem todos; a gestora não.
  Grava o sistema (cálculo da rotina), as sócias e o financeiro (pagamento, parte 2).
"""
from django.db import migrations

ADMIN = "hera_has_role(agency_id, ARRAY['admin'])"

FORWARD = f"""
ALTER TABLE crm_referral ENABLE ROW LEVEL SECURITY;
ALTER TABLE crm_referral FORCE ROW LEVEL SECURITY;
CREATE POLICY crm_referral_select ON crm_referral FOR SELECT
  USING (hera_is_system() OR hera_staff_can_view(referred_id) OR hera_staff_can_view(referrer_id) OR hera_is_own(referrer_id));
CREATE POLICY crm_referral_insert ON crm_referral FOR INSERT WITH CHECK (hera_is_system() OR {ADMIN});
CREATE POLICY crm_referral_update ON crm_referral FOR UPDATE USING (hera_is_system() OR {ADMIN}) WITH CHECK (hera_is_system() OR {ADMIN});
CREATE POLICY crm_referral_delete ON crm_referral FOR DELETE USING (hera_is_system() OR {ADMIN});

ALTER TABLE crm_referralbonus ENABLE ROW LEVEL SECURITY;
ALTER TABLE crm_referralbonus FORCE ROW LEVEL SECURITY;
CREATE POLICY crm_referralbonus_select ON crm_referralbonus FOR SELECT USING (
  hera_is_system() OR EXISTS (SELECT 1 FROM crm_referral r WHERE r.id = referral_id
    AND (hera_is_own(r.referrer_id) OR hera_has_role(r.agency_id, ARRAY['admin','financeiro']))));
CREATE POLICY crm_referralbonus_write ON crm_referralbonus FOR ALL
  USING (hera_is_system() OR EXISTS (SELECT 1 FROM crm_referral r WHERE r.id = referral_id
    AND hera_has_role(r.agency_id, ARRAY['admin','financeiro'])))
  WITH CHECK (hera_is_system() OR EXISTS (SELECT 1 FROM crm_referral r WHERE r.id = referral_id
    AND hera_has_role(r.agency_id, ARRAY['admin','financeiro'])));
"""

REVERSE = """
DROP POLICY IF EXISTS crm_referral_select ON crm_referral;
DROP POLICY IF EXISTS crm_referral_insert ON crm_referral;
DROP POLICY IF EXISTS crm_referral_update ON crm_referral;
DROP POLICY IF EXISTS crm_referral_delete ON crm_referral;
ALTER TABLE crm_referral DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS crm_referralbonus_select ON crm_referralbonus;
DROP POLICY IF EXISTS crm_referralbonus_write ON crm_referralbonus;
ALTER TABLE crm_referralbonus DISABLE ROW LEVEL SECURITY;
"""


class Migration(migrations.Migration):
    dependencies = [("web", "0013_rls_posicao_em_campanha"), ("crm", "0015_indique_e_ganhe_dados")]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
