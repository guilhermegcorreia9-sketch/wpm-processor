# Manual de Instalação e Uso do Plugin "WPM 1-meter spatial resolution"

Plugin QGIS para geração de imagens do satélite **CBERS-4A/WPM** com resolução espacial de 1 metro, a partir do catálogo STAC do **Brazil Data Cube (BDC/INPE)**. O plugin busca as cenas disponíveis para uma área de interesse, executa o pipeline de fusão de bandas pelo método **TCLT** (registro, restauração e fusão) e entrega produtos RGB e/ou NRGB prontos para uso no QGIS.

- **Versão:** 2.0.0
- **Autores:** Laércio Massaru Namikawa, Emiliano Ferreira Castejon, Guilherme Correia, Miguel Alexandre da Cunha
- **Repositório:** https://github.com/migualex/cbers-wpm-1m
- **Licença:** GNU GPL v3

---

## Requisitos

1. **QGIS** versão **3.44**.
2. **Windows** — o pipeline chama um executável (`.exe`) por meio de um script `.bat`, portanto o plugin depende de ambiente Windows.
3. **Conexão com a internet**, para consultar o catálogo STAC do BDC (`https://data.inpe.br/bdc/stac/v1/`, coleção `CB4A-WPM-L4-DN-1`) e baixar as cenas/miniaturas.
4. **Executável TCLT** (`tclt_exe.exe`), responsável pelo registro, restauração e fusão das bandas. Ele **não está incluso no pacote do plugin** e precisa ser obtido separadamente junto à equipe do INPE.
5. **Bibliotecas Python** usadas pelo pipeline, que precisam estar disponíveis no interpretador Python do QGIS: `numpy`, `requests`, `pyproj`, `geopandas`, `rasterio`, `shapely`.

---

## 1. Instalação

### 1.1. Instalar as dependências Python

O processamento roda em um subprocesso Python separado do QGIS, mas que usa o **mesmo interpretador** do QGIS — por isso as bibliotecas precisam ser instaladas nesse ambiente, e não em uma instalação Python qualquer da máquina.

1. Abra o **OSGeo4W Shell** (instalado junto com o QGIS no Windows, disponível no Menu Iniciar).
2. Execute:

   ```
   python -m pip install numpy requests pyproj geopandas rasterio shapely
   ```

3. Aguarde a instalação terminar sem erros.

**Dica:** se você não sabe qual é o interpretador Python usado pelo seu QGIS, abra o **Console Python do QGIS** (`Complementos > Console Python`) e execute `import sys; print(sys.executable)`. Use o Python dessa mesma pasta para instalar as dependências, caso não utilize o OSGeo4W Shell.

### 1.2. Instalar o plugin

1. Baixe o arquivo `v2_1_-_cbers_wpm_plugin.zip`.
2. No QGIS, vá em **Complementos > Gerenciar e Instalar Complementos**.
3. Selecione a aba **Instalar a partir do ZIP**.
4. Aponte para o arquivo `.zip` baixado e clique em **Instalar Complemento**.

Alternativamente, é possível instalar manualmente:

1. Extraia o `.zip` — isso gera a pasta `cbers_wpm_plugin`.
2. Copie essa pasta inteira para o diretório de plugins do seu perfil ativo do QGIS:

   ```
   %APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\
   ```

   (Substitua `default` pelo nome do seu perfil, caso use outro.)
3. Reinicie o QGIS.

### 1.3. Habilitar o plugin

1. Vá em **Complementos > Gerenciar e Instalar Complementos > Instalados**.
2. Marque a caixa ao lado de **"WPM 1-meter spatial resolution"**.
3. Confirme que o ícone do plugin aparece na barra de ferramentas e no menu **Complementos**.

---

## 2. Preparar o executável TCLT

Antes de rodar um processamento, tenha o `tclt_exe.exe` salvo em algum local acessível no seu computador (ex.: `C:\TCLT\tclt_exe.exe`). O caminho para esse arquivo será informado dentro do plugin, na aba **Processamento** (passo 3.2).

---

## 3. Como Usar

Abra o plugin clicando no seu ícone na barra de ferramentas, ou em **Complementos > WPM 1-meter spatial resolution**.

A janela do plugin é dividida em 4 abas: **ROI**, **Processamento**, **Produto Final** e **Execução**.

### 3.1. Aba "ROI" — definir a área de interesse

<img width="754" height="686" alt="image" src="https://github.com/user-attachments/assets/24219c8f-8adc-40ec-87b0-09298b6ea553" />

Escolha uma das duas origens da área de interesse:

- **Arquivo vetorial (Shapefile / GeoPackage):** selecione um arquivo `.shp` ou `.gpkg` contendo o polígono da área desejada.
- **Coordenada (Lat / Long):** informe a Latitude e a Longitude do ponto central e defina o **Tamanho do ROI** (entre 10 e 40 km) — o plugin monta automaticamente um retângulo (bounding box) ao redor do ponto com esse tamanho.

**Importante:** preencha apenas uma das duas opções.

### 3.2. Aba "Processamento" — buscar e selecionar cenas

<img width="824" height="684" alt="image" src="https://github.com/user-attachments/assets/e8c69137-f957-4ae6-8d36-60c056995725" />

1. Informe a **Data aproximada** desejada para a imagem.
2. Clique em **"🔍 Buscar imagens disponíveis"**. O plugin consulta o STAC do BDC dentro de uma janela de ±60 dias em torno da data informada, considerando o ROI definido na aba anterior.
3. As cenas encontradas aparecem na tabela com **Data**, **Tile** e **Dias** (distância em dias da data alvo). Clique em uma linha para carregar sua miniatura de pré-visualização.
4. Selecione a(s) cena(s) desejada(s) na tabela.

   **Importante:** só é permitida **uma cena por tile**. Se duas cenas do mesmo tile forem selecionadas ao mesmo tempo, o plugin sinaliza o conflito e impede a execução até que a seleção seja corrigida.

5. Em **"Processamento TCLT"**, informe o caminho do executável `tclt_exe.exe` (preparado no passo 2).

Se nenhuma cena for encontrada, tente uma data diferente ou revise/amplie a área de interesse na aba ROI.

### 3.3. Aba "Produto Final" — configurar a saída

<img width="824" height="685" alt="image" src="https://github.com/user-attachments/assets/f67241c9-1e54-4406-bd12-b24c9b5fe2b2" />

1. Marque os produtos que deseja gerar:
   - **Visualização RGB** (PCA / fusão pancromática) — 8 bits.
   - **Banda Bruta NGB** (NIR / Green / Blue) — 16 bits.

   É preciso marcar pelo menos um dos dois.

2. Selecione a **pasta de saída** onde os produtos finais serão salvos.
3. Escolha o **formato de saída**:
   - **GeoTIFF**, ou
   - **JPEG2000 (JP2)** — com opção **Sem perdas (lossless)**, ou, se desmarcada, um controle de **Qualidade JP2** (1–100).

### 3.4. Aba "Execução" — rodar o processamento

<img width="824" height="668" alt="image" src="https://github.com/user-attachments/assets/3e3de8e9-d605-42de-910c-8a97f8b7befa" />

1. Clique em **"▶ Executar processamento"**.
2. Acompanhe o andamento pelo log exibido nesta aba. É possível **cancelar** o processamento em andamento pelo botão **"Cancelar"**.
3. Ao concluir com sucesso, os produtos gerados são carregados automaticamente como camadas no painel de Camadas do QGIS, e uma mensagem indica a pasta e a quantidade de arquivos gerados.

**Dica:** logo após o carregamento, ajuste o contraste da visualização pelo histograma da camada, em **Propriedades da Camada > Simbologia**.

---

## 5. Exemplos

<img width="1025" height="881" alt="image" src="https://github.com/user-attachments/assets/c1ab8baa-f968-4104-ba08-60a64c113a50" />

<img width="1469" height="882" alt="image" src="https://github.com/user-attachments/assets/b3f1288d-c4f6-4014-a3cf-b8f78b530c8a" />

---

## 5. Solução de Problemas

- **"Não foi possível localizar um interpretador Python válido nesta instalação do QGIS"** — ocorre quando o QGIS foi instalado de uma forma em que o Python vem embutido no próprio executável do QGIS (`qgis-bin.exe`), sem um `python.exe`/`python3.exe` separado. Solução: instale o QGIS via **OSGeo4W** (que inclui um interpretador Python separado) ou localize um `python.exe` válido na pasta de instalação do QGIS (ex.: `.../apps/Python3XX/`).
- **Erro do TCLT relacionado a "tie-points"** — normalmente indica falta de contraste/pontos de controle entre as bandas. O plugin já tenta relaxar automaticamente o parâmetro de correlação algumas vezes antes de desistir; se o erro persistir, tente outra cena ou revise a área de interesse.
- **"Nenhuma cena encontrada"** — tente uma data diferente ou uma janela/área de interesse maior.
- **"Selecione apenas uma cena por tile"** — desmarque a cena duplicada na tabela de resultados, mantendo apenas uma por tile.

---

## 6. Referências

- Catálogo STAC do Brazil Data Cube: `https://data.inpe.br/bdc/stac/v1/` (coleção `CB4A-WPM-L4-DN-1`)
- Repositório do plugin: https://github.com/migualex/cbers-wpm-1m
