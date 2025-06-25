
🎲 Dominó com Bots em Pygame
Um jogo de Dominó clássico desenvolvido em Python com a biblioteca Pygame, onde um jogador enfrenta três oponentes controlados por computador (bots) que jogam de forma autônoma usando threads.

Nota: Para a imagem acima funcionar, grave um GIF do seu jogo, salve-o como gameplay.gif dentro da pasta imagens e suba para o seu repositório.

📖 Sobre o Projeto
Este projeto foi desenvolvido como uma forma de aplicar conceitos avançados de programação em Python, incluindo orientação a objetos, manipulação de interface gráfica e, principalmente, concorrência com threads. O objetivo era criar um jogo de Dominó funcional onde o jogador pudesse ter uma experiência fluida contra oponentes de IA, sem que a lógica dos bots travasse a interface principal.

✨ Funcionalidades
Jogador vs. Bots: Um jogador humano contra três oponentes controlados por computador.

Interface Gráfica Completa: Desenvolvido com Pygame, com menus, tabuleiro, peças e placar.

Sistema de Turnos Automatizado: O jogo gerencia os turnos de forma ordenada entre o jogador e os bots.

Inteligência Artificial Concorrente: Cada bot roda em sua própria Thread, permitindo que eles "pensem" sem congelar o jogo.

Sincronização Segura: Uso de Locks e Semáforos para garantir que as jogadas ocorram em ordem e sem conflitos de dados.

Regras Clássicas: Inicia com a maior peça dupla, sistema de pontuação até 5 vitórias e lógica de "passe" quando não há peças para jogar.

Menus Interativos: Menu principal, menu de pausa e telas de resultado de rodada e de campeão.

🛠️ Tecnologias e Conceitos
Python 3: Linguagem de programação principal.

Pygame: Biblioteca para desenvolvimento de jogos, usada para gráficos, som e entrada do usuário.

Threading: Módulo nativo do Python usado para criar os bots concorrentes.

Sincronização (Locks e Semáforos): Conceitos fundamentais de programação concorrente para gerenciar o acesso a recursos compartilhados e evitar condições de corrida.
