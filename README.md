# Relatório: Sistema de Monitoramento de Temperatura e Abertura de Porta

**Nome Completo:** Vinicius Reis de Lemos

**GitHub:** https://github.com/viniR15/

Projeto embarcado para ESP32 que monitora, ao mesmo tempo, o tempo em que
uma porta/tampa fica aberta e variações bruscas de temperatura em um
ambiente refrigerado (smart cooler / estufa). O objetivo é simular um
sistema simples de controle de qualidade: avisar quando algo sai do
esperado e avisar de novo quando tudo volta ao normal.

## Como o sistema funciona

O firmware acompanha duas condições em paralelo, sem nunca travar o loop
principal:

**1. Tempo de porta aberta.** Quando o botão (`btn1`, simulando o sensor
da porta) é solto, o sistema começa a contar o tempo. Se a porta continuar
aberta por mais de 5 segundos, dispara um alerta.

**2. Variação de temperatura.** Enquanto o ambiente está estável (porta
fechada, sem alarmes), o sistema guarda a temperatura atual como
referência. A cada leitura, compara a temperatura atual com essa
referência. Se a diferença passar de 3°C, entende que houve uma
degradação térmica e dispara um alerta imediatamente.

**3. Voltar ao normal.** O sistema só avisa que voltou ao normal quando as
duas condições estão seguras **ao mesmo tempo** — porta fechada e
temperatura estável. Se só uma das duas se resolver, o sistema continua
em alerta e explica o motivo no monitor serial.

## Por que essas escolhas (e não outras)

Aqui está o raciocínio por trás dos pontos que exigiram uma decisão de
projeto — não só o que foi feito, mas por que essa alternativa foi
escolhida entre as opções possíveis.

**Por que temporização com "relógio interno" em vez de `delay()`?**
A alternativa mais simples seria usar `delay(5000)` para esperar o tempo
limite da porta. Ela foi descartada porque, enquanto o firmware está
"dormindo" dentro de um `delay()`, ele não consegue reagir se a porta
fechar antes do tempo, nem se a temperatura mudar nesse meio-tempo — o
sistema ficaria cego para eventos concorrentes. Por isso a temporização
foi feita comparando `millis()`/`ticks_ms()` a cada volta do loop: o
sistema continua "ouvindo" os dois sensores o tempo todo, mesmo enquanto
conta o tempo de um alarme.

**Por que a referência de temperatura é dinâmica, e não um valor fixo no
código?**
Fixar um número como "20°C é a temperatura normal" funcionaria nos testes,
mas seria frágil: qualquer ambiente com temperatura de base diferente
geraria falso alarme. Por isso o sistema aprende sozinho: ele grava a
própria leitura como referência sempre que está tudo estável, e só
compara a *variação* a partir dali. Isso é o que o enunciado pede
("temperatura de referência coletada enquanto o ambiente estava
estabilizado") e também é mais realista: o risco real não é "estar frio
ou quente", é uma mudança brusca.

**Por que a normalização exige as duas condições juntas, e não cada
alarme se resolvendo de forma independente?**
Seria mais simples fazer cada alarme desligar sozinho assim que sua
própria condição voltasse ao normal (porta fecha → some o alarme de
porta, temperatura estabiliza → some o alarme térmico, cada um por conta
própria). Essa opção foi descartada porque o projeto trata os dois
alarmes como sintomas do mesmo risco — o produto guardado no cooler pode
ter sido comprometido tanto por ficar exposto quanto por esquentar demais
— então o sistema só deveria dizer "está tudo bem" quando as duas coisas
realmente estiverem seguras ao mesmo tempo. Fazer os alarmes se
desligarem de forma independente poderia mascarar um problema térmico
ainda em curso só porque a porta foi fechada.

**Por que ler o MPU6050 direto pelos registradores I2C na versão
MicroPython, em vez de usar uma biblioteca pronta?**
Na versão em C++ a biblioteca `Adafruit_MPU6050` já resolve isso. Em
MicroPython, instalar bibliotecas externas depende de um passo extra de
empacotamento que nem sempre está disponível no ambiente de simulação.
Como só a leitura de temperatura é necessária (não o giroscópio nem o
acelerômetro), optou-se por acessar diretamente os registradores
`PWR_MGMT_1` (acordar o sensor) e `TEMP_OUT_H` (ler a temperatura) via
`machine.I2C`. Isso reduz uma dependência externa e deixa o projeto
autocontido.

## Estrutura do projeto

```
├── src/main.py     # lógica completa (versão MicroPython)
├── main.py          # arquivo exigido pelo Wokwi na raiz; só chama src/main.py
├── diagram.json      # circuito simulado (ESP32 + MPU6050 + botão)
├── wokwi.toml        # configuração da simulação
└── README.md         # este documento
```

O `main.py` da raiz existe só porque o simulador exige um arquivo com
esse nome exato ali para iniciar a execução; ele não contém lógica, apenas
repassa a execução para `src/main.py`, que é onde o código de verdade
mora — assim a organização em pastas pedida é respeitada sem abrir mão do
funcionamento no Wokwi.

## Como rodar

1. Baixe o firmware genérico do MicroPython para ESP32 em
   micropython.org e salve como `firmware.bin` na raiz do projeto.
2. Abra o `diagram.json` no Wokwi (ou use a extensão do VS Code / Wokwi
   CI) e inicie a simulação.
3. Acompanhe o monitor serial: ele mostra a inicialização, os alertas e
   uma telemetria a cada segundo.

## Testes automatizados

Os cenários de teste (`test_1`, `test_2`, `test_3`) cobrem os três
comportamentos principais: alarme por tempo de porta aberta, alarme por
variação térmica e retorno ao estado normal. Todos validam mensagens
exatas via `wait-serial`, então qualquer mudança de texto nos alertas
quebra os testes propositalmente — isso garante que o contrato de
comunicação do sistema não mude sem querer.

## Possíveis melhorias futuras

- Persistir o histórico de alarmes em memória não-volátil.
- Adicionar debounce mais explícito no botão para simular ruído real de
  contato mecânico.
- Permitir configurar os limites (tempo e variação) via comando serial,
  sem precisar recompilar o firmware.

## Problemas encontrados

Os testes automatizados relacionados à proposta deste desafio não puderam ser concluídos. A causa aparente é um conflito entre o nome do SECRET sugerido (WOKWI_API_KEY) e o nome esperado pelo teste (WOKWI_CLI_TOKEN). Ainda que o nome da chave seja alterado para se adequar ao esperado pelo teste, outros problemas aparecerão (timeout) ainda relacionados a este conflito). Tendo em vista que a proposta de solução penaliza a edição de arquivos relacionados aos testes e que a possibilidade de soulução envolve essa edição, a minha solução proposta será entregue dessa maneira.
