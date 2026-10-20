# Fisco

App pessoal de estudo, instalável e offline. O conteúdo em `data/conteudo.enc` é criptografado (AES-GCM, chave derivada por PBKDF2) e só abre com a senha digitada na tela "Rumo ao Fisco".

## Atualizar o conteúdo
1. `python3 tools/parse.py` e `python3 tools/export.py` geram os pacotes a partir dos PDFs (pasta local, fora do repositório).
2. `python3 tools/build.py --codigo <senha> --pacotes <pasta> [--extra cards_resumos.json]`
3. Commit e push: o GitHub Pages publica sozinho e os aparelhos baixam a nova versão ao abrir com internet.

Nunca coloque PDFs, textos extraídos ou pacotes sem criptografia neste repositório.
