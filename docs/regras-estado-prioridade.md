# Regras do Acompanhamento Semanal — estado, sinais e prioridade

Extraído de `build_semana.py`, o script que monta a aba Desempenho do Acompanhamento Semanal. Estas são as regras que estão em uso hoje, com os limites reais. O script completo vai junto, como fonte.

## Dados de entrada

Leitura do Backstage, em **Dados do criador**, por período.

Uma linha por criador por período:

```
[display_id, income, liveDuration (segundos), validDay, pkCount, newFansClubCnt, newVideos]
```

Uma linha por criador na lista de criadores:

```
[display_id, AgentName, JoinTime, JoinedDays, LastLiveTime, FollowerAmount,
 GraduationStatus, UpgradingStatus, HostLastMonthTier]
```

São lidos sete períodos: as cinco últimas semanas (`w0` a `w4`), o mês anterior inteiro (`prev`) e o mês corrente até o domingo (`mtd`).

**Exclusões:** criadores dos agentes `contato@agenciaimpulselive.com` (Impulse) e `lunowwagency@gmail.com` (Lunow) não entram.

## Semana analisada e normal do criador

- A semana vai de **segunda a domingo, em UTC**. A leitura roda na segunda; a semana analisada é a que terminou no domingo anterior (`w4`).
- O **normal** do criador é a **mediana dos diamantes das três semanas anteriores** (`w1`, `w2`, `w3`). No código: `base = median(wD[1:4])`.
- A variação é `pct = round((wD[4] / base - 1) * 100)`, e fica indefinida quando `base = 0`.
- `since` = dias sem LIVE = `max(0, (segunda_da_leitura - dia_da_última_LIVE))`. Sem nenhuma LIVE registrada, `since = 999`.

## Segmento (tamanho do criador)

```
proj = diamantes_do_mês_até_domingo * dias_do_mês / dia_do_domingo
mref = max(diamantes_do_mês_anterior_inteiro, proj)
```

| Segmento | Faixa de `mref` |
|---|---|
| Top | ≥ 100.000 💎 |
| Médio | ≥ 20.000 💎 |
| Desenvolvimento | ≥ 2.000 💎 |
| Base | abaixo de 2.000 💎 |

Este segmento **não é o mesmo** que os grupos Bronze, Prata, Ouro e Diamante, que vêm do nível do mês anterior no TikTok. Os dois convivem: o segmento serve para priorizar a fila, o grupo serve para as campanhas internas.

## Estado da semana

Testado **nesta ordem**; o primeiro que bate define o estado.

| Ordem | Estado | Condição |
|---|---|---|
| 1 | Inativo 30d+ | `since >= 30` |
| 2 | Sem live | `since >= 7` ou (`validDay` da semana = 0 **e** horas da semana < 1 **e** `validDay` da semana anterior = 0) |
| 3 | Queda | `base >= 2000` e `pct < -30` |
| 4 | Subindo | diamantes da semana `>= 2000` e `pct >= 30` |
| 5 | Novo | dias desde a entrada `<= 30` |
| 6 | Horas sem retorno | horas da semana `>= 10` e diamantes por hora `< 150` |
| 7 | Irregular | dias válidos da semana `<= 3` |
| 8 | Estável | nenhuma das anteriores |

## Prioridade

`topmed` = segmento é Top ou Médio.

**Prioridade 1**, se qualquer uma for verdadeira:
- `topmed` e estado é Queda ou Sem live
- estado é Queda e `base >= 5000`
- estado é Subindo e (segmento é Top **ou** diamantes da semana `>= 50000`)

**Prioridade 2**, se qualquer uma for verdadeira:
- estado é Subindo ou Horas sem retorno
- estado é Novo e dias válidos da semana `> 0`
- estado é Irregular e `base >= 2000`
- estado é Estável e `topmed`

**Prioridade 3:** todo o resto. É quem recebe mensagem coletiva no modelo atual.

## Sinais

Acumulativos: um criador pode ter mais de um.

| Sinal | Condição |
|---|---|
| Quase sem batalhas | horas das duas últimas semanas `>= 20` e batalhas das duas últimas semanas `< 10` |
| Fã-clube parado | nenhum fã novo na semana e horas da semana `>= 5` |
| Sem vídeos | nenhum vídeo nas duas últimas semanas e horas das duas últimas `>= 10` |
| N dias válidos | dias válidos da semana entre 1 e 4, e o estado não é Irregular |

## Faixas de graduação

Valem para quem tem `GraduationStatus = 2` ("Não se graduou"). O mapa é `4 = criador já existente`, `2 = não se graduou`, `3 = graduado`, `1 = em andamento`.

```
prazo      = entrada + 90 dias
pace       = diamantes_do_mês_até_domingo / dia_do_domingo
falta      = max(0, 80000 - diamantes_do_mês)
proj       = diamantes_do_mês + pace * dias_que_faltam_no_mês
```

Testado nesta ordem:

| Faixa | Condição |
|---|---|
| Conferir graduação | fez 80 mil ou mais no mês anterior, mas o status ainda é "Não se graduou" |
| No radar / Em formação | o mês corrente não está na janela de 90 dias |
| Bateu 80K no mês | diamantes do mês `>= 80000` |
| No ritmo | `proj >= 80000` |
| Precisa acelerar | `proj >= 40000` |
| Difícil no mês | diamantes do mês `>= 5000` ou diamantes da semana `>= 3000` |
| No radar | horas da semana `< 3` |
| Em formação | o resto |

**Potencial de graduação**, para o 1:1 mensal e para a escolha de campanha, são as faixas **No ritmo** e **Precisa acelerar**.

## Dois pontos que mudaram depois do script

1. **Régua de reativação.** O texto de ação do script ainda diz "7, 14, 21 e 30 dias". A regra em vigor desde 12/11/2026 é **4, 14, 21 e 30 dias**. Vale a nova.
2. **Fonte dos diamantes.** O script lê Dados do criador, que fecha no dia anterior. É a fonte única do app e do painel. Receita › Incentivos, que inclui hoje, fica só para o fechamento do mês e as decisões de compra das sócias.

## Cortes do diagnóstico de queda

O script define só um desses cortes. Os outros foram decididos em 14/11/2026 e estão aqui para não serem inventados.

| Passo | Corte | Origem |
|---|---|---|
| Caíram as horas | horas da semana `< 0,7 ×` **média** das 3 semanas anteriores | já no script (`avgH`) |
| Caíram os dias | dias válidos da semana `<=` **média** das 3 anteriores `- 2` | decidido em 14/11 |
| Caíram impressões, espectadores, tempo médio, taxa de presentes, batalhas, fãs novos | 30% abaixo da **média** das 3 semanas anteriores | decidido em 14/11 |

Basta um entre horas e dias para o passo 1 responder "sim" e a conversa ser sobre rotina.

**Por que média e não mediana.** A queda de diamantes usa a **mediana** das três semanas porque um presente grande distorce uma semana inteira. Horas, dias, espectadores e batalhas não têm esse tipo de pico, então a **média** serve e é mais sensível. Não é descuido: é de propósito.

**Por que 2 dias e não 30% nos dias válidos.** Dias válidos vão de 0 a 7. Com números pequenos, a porcentagem vira ruído: de 7 para 5 dias dá -29% e não dispararia, mas são dois dias a menos de LIVE, que é exatamente o que explica uma queda de diamantes.

## Semana sem leitura própria (decisão de 19/11/2026)

O app tira as semanas da diferença entre leituras. Quando um período chega numa importação só (em 18/11/2026, novembro de 01 a 17 entrou de uma vez), essa diferença joga o período inteiro numa semana e deixa as outras vazias: uma parece sem LIVE e a outra, enorme.

Regra (`data/states.py:weeks_readable`): se alguma das 4 semanas que a leitura compara (a analisada e as 3 anteriores) não tem leitura própria, a fila **não gera** queda, subida nem semana irregular, a sugestão de visita não usa a queda e os sinais de risco dos Diamante pelos números não valem. Uma leitura que começa até 2 dias antes da semana ainda conta (um dia de importação perdido). O estado da semana continua aparecendo na ficha, só não vira item da fila. A régua sem LIVE não muda, porque usa o último dia com LIVE.

Para corrigir um mês importado de uma vez, importe as leituras acumuladas que faltam (por exemplo, de 01/11 até cada domingo: 01/11, 08/11 e 15/11).
