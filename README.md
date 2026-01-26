# README

<details open>
<summary></b>📗 Guia de Configuração</b></summary>

- 🐳 [Docker Compose](#-docker-compose)
- 🐬 [Docker environment variables](#-docker-environment-variables)
- 🐋 [Service configuration](#-service-configuration)
- 📋 [Setup Examples](#-setup-examples)

</details>

## Visão Geral

Este guia fornece instruções passo a passo para configurar o RAGFlow com integração do Ollama como provedor de LLM. O RAGFlow é um motor de Recuperação Aumentada por Geração (RAG) que permite criar bases de conhecimento e fazer perguntas sobre seus documentos usando inteligência artificial.

Pré-requisitos

- Docker e Docker Compose instalados
- Mínimo 16GB de RAM disponível
- Mínimo 50GB de espaço em disco
- Windows com WSL2 (ou Linux/macOS)

## Etapa 1: Iniciar os Serviços Docker
**1.1 Navegar até a pasta do projeto**


**1.2 Iniciar todos os containers**
Execute o comando para iniciar todos os serviços:
  `docker-compose up -d`

Saída esperada:
[+]: # "Running 8/8"
 ✔ Container es01                 Running
 ✔ Container mysql                Healthy
 ✔ Container minio                Running
 ✔ Container redis                Running
 ✔ Container ollama               Running
 ✔ Container ragflow              Running
 ✔ Container crewai_app           Running

 1.3 Verificar o status dos containers

Para confirmar que todos os serviços estão rodando corretamente:

docker-compose ps

Todos os containers devem aparecer com status Up ou Healthy.

1.4 Aguardar a inicialização completa

O RAGFlow pode levar de 3 a 5 minutos para inicializar completamente na primeira execução. Para acompanhar o progresso:

Bash

docker logs -f ragflow
docker logs -f ragflow

Aguarde até ver a mensagem:

Plain Text

 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:9380

Etapa 2: Instalar Modelos do Ollama

2.1 Instalar o modelo de chat (Llama 3.1 )

O Ollama é um servidor de LLM local que fornece modelos de linguagem. Instale o modelo principal:

Bash

docker exec -it ollama ollama pull llama3.1

Este comando pode levar alguns minutos, dependendo da sua conexão de internet. O modelo tem aproximadamente 4.7GB.

Saída esperada:

Plain Text

pulling manifest
pulling 8934d3f265a7
pulling 5c40d7dd6c4f
...
success

2.2 Instalar o modelo de embedding

Para que o RAGFlow possa vetorizar seus documentos, instale um modelo de embedding:

Bash

docker exec -it ollama ollama pull nomic-embed-text

Ou, alternativamente:

Bash

docker exec -it ollama ollama pull mxbai-embed-large

Nota: O modelo de embedding é menor (~300MB) e essencial para a busca semântica.

2.3 Verificar modelos instalados

Para confirmar que os modelos foram instalados corretamente:

Bash

docker exec -it ollama ollama list

Saída esperada:

Plain Text

NAME                    ID              SIZE      MODIFIED
llama3.1:latest         365c0bd3c000    4.7GB     2 minutes ago
nomic-embed-text:latest 0d3e4823be78    274MB     1 minute ago

Etapa 3: Configurar o RAGFlow

3.1 Acessar a interface do RAGFlow

Abra seu navegador e acesse:

Plain Text

http://localhost

Você deve ver a tela inicial do RAGFlow.

3.2 Criar uma conta

1.Clique em Sign Up (ou Registrar )

2.Preencha os dados:

•Email: seu-email@exemplo.com

•Senha: escolha uma senha segura
•Confirmar Senha: repita a senha

3.Clique em Sign Up para criar a conta

4.Faça login com suas credenciais

3.3 Configurar o Ollama como provedor de LLM

3.3.1 Acessar as configurações

1.Clique no ícone de engrenagem (⚙️) no canto superior direito

2.Selecione Model Providers ou Provedores de Modelo

3.3.2 Adicionar o modelo de Chat

1.Clique em Add Model Provider ou Adicionar Provedor

2.Selecione Ollama da lista

3.Preencha os campos:

Campo
Valor
Model type
chat
Model name
llama3.1
Base url
http://ollama:11434
API-Key
(deixe em branco )
Max tokens
4096

1.Clique em Save ou Salvar

3.3.3 Adicionar o modelo de Embedding

1. Clique novamente em Add Model Provider

2. Selecione Ollama

3. Preencha os campos:

Campo
Valor
Model type
embedding
Model name
nomic-embed-text
Base url
http://ollama:11434
API-Key
(deixe em branco )
Max tokens
512

1.Clique em Save ou Salvar

Resultado esperado: Ambos os modelos devem aparecer na lista de provedores com status ✓ (verificado).

Etapa 4: Criar e Configurar um Dataset

4.1 Acessar a seção de Knowledge Base

1.No menu lateral, clique em Knowledge Base ou Base de Conhecimento

2.Clique em Create Dataset ou Criar Dataset

4.2 Configurar o Dataset

1.Preencha os dados:

•Dataset Name: Nome descritivo (ex: "Políticas de Crédito")

•Description: Descrição do conteúdo (ex: "Documentos sobre políticas de crédito e regulamentações")

2.Configure as opções:

• Embedding Model: Selecione nomic-embed-text (ou o modelo que você instalou)

• Chunk Size: 800 (tamanho dos pedaços de texto)

• Overlap: 100 (sobreposição entre chunks)

3.Clique em Create ou Criar

4.3 Fazer upload de arquivos

4.3.1 Preparar os documentos

Prepare seus documentos em um dos formatos suportados:

• PDF (.pdf)

• Word (.docx, .doc)

• Texto (.txt)

• Markdown (.md)

• Imagens (.png, .jpg, .jpeg)

Dica: Para melhores resultados, use documentos bem estruturados e sem muitas imagens.

4.3.2 Fazer upload

1.Acesse o dataset que você criou

2.Clique em Upload ou Fazer Upload

3.Selecione um ou mais arquivos do seu computador

4.Clique em Upload para enviar

Exemplo de arquivos úteis:

•
Políticas de crédito da instituição

•
Regulamentações do Banco Central

•
Manuais de procedimentos

•
Documentos de compliance

4.4 Aguardar o processamento

O RAGFlow processará os documentos:

1.Extração de texto: Extrai o conteúdo dos arquivos

2.Chunking: Divide o texto em pedaços menores

3.Embedding: Converte os chunks em vetores semânticos

4.Indexação: Armazena os vetores no Elasticsearch

Tempo estimado: 1-5 minutos por documento, dependendo do tamanho.

Você pode acompanhar o progresso na interface. Quando terminar, o status mudará para Completed ou Concluído.

4.5 Verificar o Dataset

1.Clique no dataset para abrir os detalhes

2.Você deve ver:

•Número de documentos processados

•Número de chunks criados

•Status de indexação

Etapa 5: Testar o Sistema

5.1 Fazer uma pergunta ao Dataset

1.No dataset, clique em Chat ou Conversa

2.Digite uma pergunta sobre o conteúdo dos seus documentos

3.Exemplo: "Qual é a taxa de juros padrão para crédito pessoa física?"

4.Pressione Enter ou clique em Send

O RAGFlow deve:

1.Buscar documentos relevantes

2.Enviar para o Ollama processar

3.Retornar uma resposta baseada nos documentos

5.2 Verificar a qualidade das respostas

•As respostas devem ser baseadas nos documentos
•Deve haver referências aos documentos usados
•A resposta deve ser relevante e precisa

Etapa 6: Obter Credenciais para Integração

Se você deseja integrar o RAGFlow com o sistema de agentes (CrewAI), você precisará:

6.1 Obter a API Key

1.Vá em Settings > API Keys

2.Clique em Create API Key ou Criar Chave de API

3.Dê um nome descritivo (ex: "CrewAI Integration")

4.Copie a chave gerada

5.Guarde em local seguro - você não poderá ver novamente

6.2 Obter o Dataset ID

1.Vá em Knowledge Base

2.Clique no dataset que você criou

3.O ID está na URL: http://localhost/knowledge/datasets/{DATASET_ID}

4.Copie o DATASET_ID

6.3 Atualizar o arquivo .env

Se estiver usando o sistema de agentes, atualize o arquivo .env:

Plain Text

RAGFLOW_API_KEY=sua-chave-aqui
RAGFLOW_DATASET_ID=seu-dataset-id-aqui

Solução de Problemas

Problema: Página "Welcome to nginx"

Solução:

1.Aguarde mais alguns minutos (até 5 minutos na primeira execução )

2.Tente acessar http://localhost:9380 diretamente

3.Verifique os logs: docker logs ragflow

Problema: Ollama não responde

Solução:

Bash

# Verifique se o container está rodando
docker ps | grep ollama

# Veja os logs
docker logs ollama

# Reinicie o container
docker restart ollama

Problema: Modelos não aparecem na lista

Solução:

1.Verifique se os modelos foram instalados: docker exec -it ollama ollama list
2.Reinicie o RAGFlow: docker restart ragflow
3.Atualize a página do navegador (Ctrl+F5 )

Problema: Upload de arquivo falha

Solução:

1.Verifique o tamanho do arquivo (máximo recomendado: 100MB)
2.Verifique se o formato é suportado
3.Verifique os logs: docker logs ragflow
4.Tente fazer upload de um arquivo menor primeiro

Problema: Elasticsearch não inicia

Solução:

Bash

# Aumentar o limite de memória no WSL2
wsl -d docker-desktop -u root
sysctl -w vm.max_map_count=262144
exit

# Reiniciar os containers
docker-compose down
docker-compose up -d

Serviços e Portas

Serviço
URL
Descrição
RAGFlow
http://localhost
Interface web principal
RAGFlow API
http://localhost:9380
API REST do RAGFlow
Ollama
http://localhost:11434
API do Ollama
MinIO
http://localhost:9001
Console de armazenamento
MySQL
localhost:3306
Banco de dados
Elasticsearch
localhost:9200
Motor de busca
Redis
localhost:6379
Cache

Próximos Passos

Após configurar o RAGFlow, você pode:

1.Criar múltiplos datasets para diferentes áreas de conhecimento

2.Integrar com o sistema de agentes (CrewAI ) para análises automáticas

3.Configurar webhooks para automações

4.Usar a API REST para integração com outras aplicações

5.Fazer backup dos datasets regularmente

Referências

• RAGFlow Documentação: https://github.com/infiniflow/ragflow
• Ollama Documentação: https://ollama.ai
• Docker Compose: https://docs.docker.com/compose/
