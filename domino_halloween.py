import pygame
import sys
import threading
import time
import random

# --- Inicialização do Pygame ---
pygame.init()
largura_tela = 1500
altura_tela = 750
screen = pygame.display.set_mode((largura_tela, altura_tela))
pygame.display.set_caption("Dominó - Jogador vs Bots com Threads")
font = pygame.font.Font(None, 36)
font_grande = pygame.font.Font(None, 50)

# --- Cores ---
BRANCO = (255, 255, 255); VERMELHO = (200, 0, 0); AMARELO = (255, 255, 0)
CINZA = (100, 100, 100); VERDE_ESCURO = (0, 100, 0); AZUL_ESCURO = (0, 0, 100)

# --- Carregamento de Imagens e Definições de Tamanho ---
try:
    background_image = pygame.image.load("imagens/tabuleiro sem peça.png")
    background_image = pygame.transform.scale(background_image, (largura_tela, altura_tela))
    verso_base = pygame.image.load("imagens/verso.png")
except pygame.error as e:
    print(f"Erro ao carregar imagem essencial: {e}"); sys.exit()

try:
    background_menu = pygame.image.load("imagens/fundo.jpg")
    background_menu = pygame.transform.scale(background_menu, (largura_tela, altura_tela))
except pygame.error as e:
    print(f"Erro ao carregar imagem de fundo do menu: {e}")
    background_menu = None


altura_peca = 80; largura_peca = altura_peca // 2
verso_vertical = pygame.transform.scale(verso_base, (largura_peca, altura_peca))
verso_horizontal = pygame.transform.rotate(verso_vertical, 90)

# --- Classe para representar uma peça de Dominó ---
class Domino:
    def __init__(self, val1, val2):
        self.val1 = val1; self.val2 = val2
        self.imagem = self.carregar_imagem()
        self.rect = None; self.inverter_visual = False

    def carregar_imagem(self):
        nome_arquivo = f"{min(self.val1, self.val2)}{max(self.val1, self.val2)}"
        try:
            img = pygame.image.load(f"imagens/{nome_arquivo}.png")
            return pygame.transform.scale(img, (largura_peca, altura_peca))
        except pygame.error:
            print(f"Aviso: Imagem 'imagens/{nome_arquivo}.png' não encontrada.")
            surf = pygame.Surface((largura_peca, altura_peca)); surf.fill(VERMELHO)
            return surf

# --- Classe para controlar o estado do jogo ---


class GameState:
    def __init__(self, num_players=4):
        self.num_players = num_players
        self.vitorias = [0] * num_players
        self.peca_encaixada_em_bucha = False
        self.empate_anterior = False
        self.maos = [[] for _ in range(num_players)]
        self.tabuleiro = []
        self.pontas = [-1, -1]
        self.turno_atual = -1
        self.vencedor = -1
        self.peca_inicial_obj = None
        self.semaphores = [threading.Semaphore(0) for _ in range(num_players)]
        self.lock = threading.Lock()
        self.passes_consecutivos = 0  # NOVO

    def distribuir_pecas(self):
        todas_as_pecas = [Domino(i, j) for i in range(7) for j in range(i, 7)]
        random.shuffle(todas_as_pecas)
        for i in range(self.num_players):
            self.maos[i] = todas_as_pecas[i*7:(i+1)*7]

        maior_carroca, jogador_inicial, peca_inicial = -1, -1, None
        for i, mao in enumerate(self.maos):
            for peca in mao:
                if peca.val1 == peca.val2 and peca.val1 > maior_carroca:
                    maior_carroca, jogador_inicial, peca_inicial = peca.val1, i, peca

        if jogador_inicial != -1:
            self.turno_atual = jogador_inicial
            print(f"Jogador {self.turno_atual + 1} começa por ter a maior dupla.")

        if not peca_inicial and self.maos[self.turno_atual]:
            self.peca_inicial_obj = self.maos[self.turno_atual][0]
        else:
            self.peca_inicial_obj = peca_inicial

        if self.turno_atual > 0 and peca_inicial:
            with self.lock:
                executar_jogada(self, peca_inicial, 'dir', self.turno_atual)

        print(f"Jogador {self.turno_atual} começa o jogo.")
        self.semaphores[self.turno_atual].release()

    def passar_a_vez(self):
        print(f"Jogador {self.turno_atual} passou a vez.")
        self.passes_consecutivos += 1
        self.turno_atual = (self.turno_atual + 1) % self.num_players
        self.semaphores[self.turno_atual].release()

    def verifica_campeao(self):
        for i, vitorias in enumerate(self.vitorias):
            if vitorias >= 5:
                return i  # Retorna o ID do jogador campeão
        return -1 # Retorna -1 se ninguém ganhou ainda

    def contabilizar_pontos(self, player_id, peca_final):
        """
        Contabiliza os pontos da rodada.
        - 1 Ponto por vitória normal.
        - 2 Pontos se a última peça for uma dupla que encaixa dos dois lados.
        """
        pontos_da_rodada = 1
        is_double = peca_final.val1 == peca_final.val2

        # Condição para pontuação especial
        if is_double:
            ponta_esq, ponta_dir = self.pontas
            # Verifica se a dupla poderia ser jogada em AMBAS as pontas ANTES da jogada final
            if peca_final.val1 == ponta_esq and peca_final.val2 == ponta_dir:
                pontos_da_rodada = 2
                print(f"PONTUAÇÃO ESPECIAL! Jogador {player_id + 1} ganha 2 pontos!")

        self.vitorias[player_id] += pontos_da_rodada
        self.vencedor = player_id
        print(f"Vitória de {pontos_da_rodada} ponto(s) para o Jogador {player_id + 1}")

    # ALTERADO: Agora só verifica a condição de vitória
    def verificar_vitoria(self, player_id):
        if not self.maos[player_id]:
            return True
        return False

    def exibir_vitorias(self):
        y = 10
        for i, vitorias in enumerate(self.vitorias):
            texto = font.render(f"Jogador {i + 1}: {vitorias} vitórias", True, BRANCO)
            screen.blit(texto, (10, y))
            y += 30
    def reset_rodada(self):
        self.peca_encaixada_em_bucha = False
        self.empate_anterior = False
        self.maos = [[] for _ in range(self.num_players)]
        self.tabuleiro = []
        self.pontas = [-1, -1]
        self.turno_atual = -1
        self.vencedor = -1
        self.peca_inicial_obj = None
        self.semaphores = [threading.Semaphore(0) for _ in range(self.num_players)]
        self.passes_consecutivos = 0






    def contabilizar_vitoria(self, player_id):
        # Adiciona uma vitória ao jogador e marca como último vencedor
         if 0 <= player_id < len(self.vitorias):
            self.vitorias[player_id] += 1
            self.vencedor = player_id
            print(f"Vitória contabilizada para o Jogador {player_id + 1}")

    
    def verificar_vitoria(self, player_id):
        if not self.maos[player_id]: 
            self.vencedor = player_id
            self.contabilizar_vitoria(player_id)  # Conta a vitória
            return True
        return False
    
    def exibir_vitorias(self):
        y = 50
        for i, vitorias in enumerate(self.vitorias):
            texto = font.render(f"Jogador {i + 1}: {vitorias} vitórias", True, BRANCO)
            screen.blit(texto, (100, y))
            y += 30
    


# --- Classe para os Bots (Threads) ---
class Bot(threading.Thread):
    def __init__(self, player_id, game_state):
        super().__init__(); self.player_id = player_id; self.game_state = game_state; self.daemon = True

    def run(self):
        while self.game_state.vencedor == -1:
            self.game_state.semaphores[self.player_id].acquire()
            if self.game_state.vencedor != -1: break

        # NOVO: Verificação de empate no início do turno do bot
            with self.game_state.lock:
                if self.game_state.passes_consecutivos >= self.game_state.num_players:
                    if self.game_state.vencedor == -1: # Garante que o empate seja setado apenas uma vez
                        print("Empate detectado no turno do Bot!")
                        self.game_state.vencedor = -2
                    break # Encerra o loop do bot

            time.sleep(random.uniform(1.0, 2.5))
            with self.game_state.lock:
                if self.game_state.turno_atual != self.player_id or self.game_state.vencedor != -1: continue
            
                mao_bot = self.game_state.maos[self.player_id]; ponta_esq, ponta_dir = self.game_state.pontas
                peca_a_jogar, lado_a_jogar = None, None
                for peca in mao_bot:
                    if ponta_esq == -1 or peca.val1 == ponta_esq or peca.val2 == ponta_esq:
                        peca_a_jogar, lado_a_jogar = peca, 'esq'; break
                    elif peca.val1 == ponta_dir or peca.val2 == ponta_dir:
                        peca_a_jogar, lado_a_jogar = peca, 'dir'; break
            
                if peca_a_jogar:
                    executar_jogada(self.game_state, peca_a_jogar, lado_a_jogar, self.player_id)
                    # A vez só é passada aqui se o bot jogar.
                    self.game_state.turno_atual = (self.game_state.turno_atual + 1) % self.game_state.num_players
                    self.game_state.semaphores[self.game_state.turno_atual].release()
                else: 
                    # Se não jogar, o bot simplesmente passa a vez.
                    self.game_state.passar_a_vez()

# --- Funções Auxiliares e de Desenho ---
def executar_jogada(game_state, peca, lado_escolhido, player_id):
    # Salva as pontas ANTES da jogada, para a lógica de pontuação especial
    pontas_antes = game_state.pontas[:]
    
    # Verifica se esta é a jogada da vitória
    eh_jogada_final = len(game_state.maos[player_id]) == 1

    if not game_state.tabuleiro:
        game_state.tabuleiro.append(peca)
        if not game_state.peca_inicial_obj: game_state.peca_inicial_obj = peca
        game_state.pontas = [peca.val1, peca.val2]
    else:
        ponta_esq, ponta_dir = game_state.pontas
        peca.inverter_visual = False
        if lado_escolhido == 'esq':
            if peca.val1 == ponta_esq:
                peca.inverter_visual = True
                game_state.pontas[0] = peca.val2
            else:
                game_state.pontas[0] = peca.val1
            game_state.tabuleiro.insert(0, peca)
        elif lado_escolhido == 'dir':
            if peca.val2 == ponta_dir:
                peca.inverter_visual = True
                game_state.pontas[1] = peca.val1
            else:
                game_state.pontas[1] = peca.val2
            game_state.tabuleiro.append(peca)

    print(f"Jogador {player_id} jogou [{peca.val1}|{peca.val2}] na ponta {lado_escolhido}.")
    game_state.maos[player_id].remove(peca)
    game_state.passes_consecutivos = 0

    # NOVO: Lógica de pontuação chamada aqui
    if eh_jogada_final:
        # Passa as pontas de ANTES da jogada para o método
        game_state_temporario = game_state
        game_state_temporario.pontas = pontas_antes
        game_state.contabilizar_pontos(player_id, peca)

def desenhar_mao_jogador(mao):
    if not mao: return
    espacamento = 10; largura_total = len(mao) * largura_peca + (len(mao) - 1) * espacamento
    x = (largura_tela - largura_total) // 2; y = altura_tela - altura_peca - 80
    for peca in mao:
        peca.rect = pygame.Rect(x, y, largura_peca, altura_peca); screen.blit(peca.imagem, peca.rect)
        x += largura_peca + espacamento

def desenhar_maos_bots(maos_bots):
    espacamento = 10; margin = 70; mao_top = maos_bots[1]
    if mao_top:
        largura_total = len(mao_top) * largura_peca + (len(mao_top) - 1) * espacamento
        x_top = (largura_tela - largura_total) // 2
        for _ in mao_top: screen.blit(verso_vertical, (x_top, margin)); x_top += largura_peca + espacamento
    mao_left = maos_bots[0]
    if mao_left:
        peca_larg, peca_alt = verso_horizontal.get_size(); altura_total = len(mao_left) * peca_alt + (len(mao_left) - 1) * espacamento
        y_left = (altura_tela - altura_total) // 2
        for _ in mao_left: screen.blit(verso_horizontal, (margin, y_left)); y_left += peca_alt + espacamento
    mao_right = maos_bots[2]
    if mao_right:
        peca_larg, peca_alt = verso_horizontal.get_size(); altura_total = len(mao_right) * peca_alt + (len(mao_right) - 1) * espacamento
        y_right = (altura_tela - altura_total) // 2; x_right = largura_tela - peca_larg - margin
        for _ in mao_right: screen.blit(verso_horizontal, (x_right, y_right)); y_right += peca_alt + espacamento

# Código corrigido para desenhar corretamente as peças no tabuleiro, respeitando orientação e inversão
def desenhar_tabuleiro(game_state):
    tabuleiro = game_state.tabuleiro
    if not tabuleiro: return

    margin = 150
    pecas_desenhadas = []

    try:
        anchor_index = tabuleiro.index(game_state.peca_inicial_obj)
    except (ValueError, AttributeError):
        anchor_index = 0
    anchor_peca = tabuleiro[anchor_index]

    is_double = anchor_peca.val1 == anchor_peca.val2
    img_anchor = anchor_peca.imagem if is_double else pygame.transform.rotate(anchor_peca.imagem, 90)
    rect_anchor = img_anchor.get_rect(center=(largura_tela / 2, altura_tela / 2))
    pecas_desenhadas.append({'img': img_anchor, 'rect': rect_anchor})

    def desenhar_corrente(pecas, p_conexao_inicial, direcao_inicial, lado):
        ponto_conexao = p_conexao_inicial
        direcao = direcao_inicial
        rect_anterior = rect_anchor

        # NOVO: Flags para controlar o estado das curvas e o espelhamento
        a_corrente_esquerda_virou_para_baixo = False
        a_corrente_esquerda_virou_para_direita = False
        a_corrente_direita_virou_para_esquerda = False

        for peca in pecas:
            is_double = peca.val1 == peca.val2
            img = peca.imagem

            if is_double:
                img = pygame.transform.rotate(img, 90 if direcao[1] != 0 else 0)
            else:
                img = pygame.transform.rotate(img, 0 if direcao[1] != 0 else 90)

            rect = img.get_rect()
            if direcao == (1, 0): rect.midleft = ponto_conexao
            elif direcao == (-1, 0): rect.midright = ponto_conexao
            elif direcao == (0, 1): rect.midtop = ponto_conexao

            nova_direcao = direcao
            if (direcao == (1, 0) and rect.right > largura_tela - margin): nova_direcao = (0, 1)
            elif (direcao == (-1, 0) and rect.left < margin): nova_direcao = (0, 1)
            elif (direcao == (0, 1) and rect.bottom > altura_tela - margin):
                nova_direcao = (-1, 0) if lado == 'dir' else (1, 0)

            if nova_direcao != direcao:
                direcao_antiga = direcao
                direcao = nova_direcao
                
                # NOVO: Lógica para "levantar as bandeiras" quando uma curva específica acontece
                if lado == 'esq':
                    if direcao_antiga == (-1, 0) and direcao == (0, 1):
                        a_corrente_esquerda_virou_para_baixo = True
                    elif direcao_antiga == (0, 1) and direcao == (1, 0):
                        a_corrente_esquerda_virou_para_direita = True
                elif lado == 'dir':
                    if direcao_antiga == (0, 1) and direcao == (-1, 0):
                        a_corrente_direita_virou_para_esquerda = True

                if is_double:
                    img = pygame.transform.rotate(peca.imagem, 90 if direcao[1] != 0 else 0)
                else:
                    img = pygame.transform.rotate(peca.imagem, 0 if direcao[1] != 0 else 90)
                
                rect = img.get_rect()

                if direcao_antiga == (1, 0) and direcao == (0, 1):
                    rect.topleft = rect_anterior.topright
                elif direcao_antiga == (-1, 0) and direcao == (0, 1):
                    rect.topright = rect_anterior.topleft
                elif direcao_antiga == (0, 1) and direcao == (-1, 0) and lado == 'dir':
                    rect.bottomright = rect_anterior.bottomleft
                elif direcao_antiga == (0, 1) and direcao == (1, 0) and lado == 'esq':
                    rect.bottomleft = rect_anterior.bottomright

            flip_x, flip_y = False, False
            if peca.inverter_visual:
                flip_x = (direcao[0] != 0)
                flip_y = (direcao[1] != 0)
            
            # --- NOVO: LÓGICA DE ESPELHAMENTO BASEADA NAS FLAGS ---
            # Regra 1: Corrente da esquerda, após virar para baixo
            if a_corrente_esquerda_virou_para_baixo and not a_corrente_esquerda_virou_para_direita:
                if direcao == (0, 1): # Se estiver na seção vertical
                    flip_y = not flip_y # Espelha verticalmente

            # Regra 2: Corrente da esquerda, após virar para a direita
            if a_corrente_esquerda_virou_para_direita:
                if direcao == (1, 0): # Se estiver na nova seção horizontal
                    flip_x = not flip_x # Espelha horizontalmente

            # Regra 3: Corrente da direita, após virar para a esquerda
            if a_corrente_direita_virou_para_esquerda:
                if direcao == (-1, 0): # Se estiver na nova seção horizontal
                    flip_x = not flip_x # Espelha horizontalmente
            # --- FIM DA LÓGICA DE ESPELHAMENTO ---

            if flip_x or flip_y:
                img = pygame.transform.flip(img, flip_x, flip_y)

            pecas_desenhadas.append({'img': img, 'rect': rect})
            
            if direcao == (1, 0): ponto_conexao = rect.midright
            elif direcao == (-1, 0): ponto_conexao = rect.midleft
            elif direcao == (0, 1): ponto_conexao = rect.midbottom
            
            rect_anterior = rect

    desenhar_corrente(tabuleiro[anchor_index+1:], rect_anchor.midright, (1,0), 'dir')
    desenhar_corrente(reversed(tabuleiro[:anchor_index]), rect_anchor.midleft, (-1,0), 'esq')

    for p in pecas_desenhadas:
        screen.blit(p['img'], p['rect'])

def desenhar_info(game_state):
    if game_state.vencedor != -1:
       empate = game_state.vencedor == -2
       vencedor = game_state.vencedor
       tela_final(empate=empate, vencedor=vencedor)
       return

    elif game_state.turno_atual == 0:
       texto_turno = font.render("Sua vez de jogar!", True, BRANCO)
       screen.blit(texto_turno, (largura_tela / 2 - texto_turno.get_width() / 2, altura_tela - 250))


    game_state.exibir_vitorias()



def jogador_tem_jogada_valida(game_state):
    mao = game_state.maos[0]
    ponta_esq, ponta_dir = game_state.pontas
    
    # Se o tabuleiro está vazio, qualquer peça é válida
    if ponta_esq == -1:
        return True
    
    # Verifica se alguma peça da mão encaixa em alguma ponta
    for peca in mao:
        if (
            peca.val1 == ponta_esq or peca.val2 == ponta_esq or
            peca.val1 == ponta_dir or peca.val2 == ponta_dir
        ):
            return True
    return False

# --- Mostrar quem está jogando ---
def mostrar_turno_atual(game_state):
    nomes = ["Você", "Bot 2", "Bot 3", "Bot 4"]
    turno = game_state.turno_atual
    if turno == -1: 
        return
    nome_turno = nomes[turno]
    cor = BRANCO if turno == 0 else VERMELHO

    texto = font.render(f"Vez de: {nome_turno}", True, cor)
    # Novo posicionamento no canto superior direito:
    x = largura_tela - texto.get_width() - 40  # 20px de margem direita
    y = 20  # 20px de margem do topo
    screen.blit(texto, (x, y))

# --- Mostrar Regras ---
def mostrar_regras():
    esperando = True
    while esperando:
        screen.fill((30, 30, 30))
        titulo = font_grande.render("Regras do Dominó", True, BRANCO)
        regras = [
            "1. Cada jogador começa com 7 peças.",
            "2. A peça inicial é a maior dupla (ex: [6|6]).",
            "3. O jogo segue em turnos no sentido horário.",
            "4. Só é possível jogar peças que combinem com as pontas.",
            "5. Se não tiver jogada válida, passe a vez.",
            "6. Vence quem ficar sem peças primeiro."
        ]
        screen.blit(titulo, (largura_tela//2 - titulo.get_width()//2, 50))

        for i, linha in enumerate(regras):
            texto = font.render(linha, True, BRANCO)
            screen.blit(texto, (100, 150 + i * 40))

        texto_voltar = font.render("Pressione ESC para voltar", True, VERMELHO)
        screen.blit(texto_voltar, (largura_tela - 350, altura_tela - 50))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                esperando = False

        pygame.display.flip()

def mostrar_pontuacoes():
    esperando = True
    while esperando:
        screen.fill((20, 20, 20))
        titulo = font_grande.render("Pontuações", True, BRANCO)
        screen.blit(titulo, (largura_tela//2 - titulo.get_width()//2, 100))

        texto = font.render("As pontuações são mostradas no topo durante o jogo.", True, BRANCO)
        screen.blit(texto, (largura_tela//2 - texto.get_width()//2, 250))

        texto_voltar = font.render("Pressione ESC para voltar", True, VERMELHO)
        screen.blit(texto_voltar, (largura_tela - 350, altura_tela - 50))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                esperando = False

        pygame.display.flip()  

# --- Exibir Controles
def exibir_controles():
    controles_texto = [
        "Controles do Jogo:",
        "Esc: Pausar o Jogo",
        "Seta para cima: Mover para cima no menu",
        "Seta para baixo: Mover para baixo no menu",
        "Enter: Selecionar opção no menu",
        "Clique: Jogar uma peça"
    ]

    clock = pygame.time.Clock()

    while True:
        screen.fill((20, 20, 20))
        titulo = font_grande.render("Controles", True, BRANCO)
        screen.blit(titulo, (largura_tela // 2 - titulo.get_width() // 2, 150))

        for i, linha in enumerate(controles_texto):
            texto = font.render(linha, True, BRANCO)
            screen.blit(texto, (largura_tela // 2 - texto.get_width() // 2, 250 + i * 40))

        texto_voltar = font.render("Pressione ESC para voltar", True, VERMELHO)
        screen.blit(texto_voltar, (largura_tela // 2 - texto_voltar.get_width() // 2, 350 + len(controles_texto) * 40))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:  # Sai da tela de controles e volta ao menu principal
                    return

        pygame.display.flip()
        clock.tick(30)

# --- Função de Menu ---
def menu_principal():
    opcoes = ["Iniciar Jogo", "Controles", "Sair"]
    selecionado = 0
    clock = pygame.time.Clock()
    

    while True:
        if background_menu:
          screen.blit(background_menu, (0, 0))
        else:
         screen.fill((20, 20, 20))


        for i, opcao in enumerate(opcoes):
            cor = VERMELHO if i == selecionado else BRANCO

            texto = font.render(opcao, True, cor)
            screen.blit(texto, (largura_tela // 2 - texto.get_width() // 2, 250 + i * 60))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selecionado = (selecionado - 1) % len(opcoes)
                elif event.key == pygame.K_DOWN:
                    selecionado = (selecionado + 1) % len(opcoes)
                elif event.key == pygame.K_RETURN:
                    if opcoes[selecionado] == "Iniciar Jogo":
                        return "jogo"
                    elif opcoes[selecionado] == "Controles":
                        exibir_controles()  # Exibe os controles quando a opção for selecionada
                    elif opcoes[selecionado] == "Sair":
                        pygame.quit()
                        sys.exit()

        pygame.display.flip()
        clock.tick(30)
        
# --- Menu depois que a partida acaba ---
def menu_pausa():
    opcoes = ["Continuar", "Reiniciar", "Voltar ao Menu Principal"]
    selecionado = 0
    clock = pygame.time.Clock()

    while True:
        screen.fill((20, 20, 20))
        titulo = font_grande.render("Pausa", True, BRANCO)
        screen.blit(titulo, (largura_tela // 2 - titulo.get_width() // 2, 150))

        for i, opcao in enumerate(opcoes):
            cor = VERMELHO if i == selecionado else BRANCO
            texto = font.render(opcao, True, cor)
            screen.blit(texto, (largura_tela // 2 - texto.get_width() // 2, 250 + i * 60))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selecionado = (selecionado - 1) % len(opcoes)
                elif event.key == pygame.K_DOWN:
                    selecionado = (selecionado + 1) % len(opcoes)
                elif event.key == pygame.K_RETURN:
                    return opcoes[selecionado]

        pygame.display.flip()
        clock.tick(30)
 

def tela_final(empate=False, vencedor=-1):
    while True:
        screen.fill((0, 0, 0))
        msg = "Empate!" if empate else "Fim da rodada!"
        texto = font_grande.render(msg, True, BRANCO)

        # Determina quem venceu
        if not empate:
            if vencedor == 0:
                resultado_texto = "Você venceu!"
            else:
                resultado_texto = f"Jogador {vencedor + 1} venceu!"
        else:
            resultado_texto = "Rodada empatada!"

        texto_resultado = font_grande.render(resultado_texto, True, BRANCO)

        sair = font.render("Pressione ESC para sair", True, CINZA)
        continuar = font.render("Pressione ENTER para próxima rodada", True, VERDE_ESCURO)

        screen.blit(texto, (largura_tela // 2 - texto.get_width() // 2, 100))
        screen.blit(texto_resultado, (largura_tela // 2 - texto_resultado.get_width() // 2, 180))
        screen.blit(sair, (largura_tela // 2 - sair.get_width() // 2, 320))
        screen.blit(continuar, (largura_tela // 2 - continuar.get_width() // 2, 360))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                elif event.key == pygame.K_RETURN:
                    return
    
def tela_campeao_final(campeao_id, placar_final):
    while True:
        screen.fill((20, 20, 20))
        
        # Título
        titulo = font_grande.render("FIM DE JOGO!", True, AMARELO) # Use a cor que preferir
        screen.blit(titulo, (largura_tela // 2 - titulo.get_width() // 2, 100))

        # Mensagem do Campeão
        if campeao_id == 0:
            msg_campeao = "Você é o grande campeão!"
        else:
            msg_campeao = f"O Jogador {campeao_id + 1} é o grande campeão!"
        
        texto_campeao = font_grande.render(msg_campeao, True, BRANCO)
        screen.blit(texto_campeao, (largura_tela // 2 - texto_campeao.get_width() // 2, 200))

        # Placar Final
        placar_titulo = font.render("Placar Final:", True, BRANCO)
        screen.blit(placar_titulo, (largura_tela // 2 - placar_titulo.get_width() // 2, 300))
        for i, pontos in enumerate(placar_final):
            nome = "Você" if i == 0 else f"Jogador {i+1}"
            texto_placar = font.render(f"{nome}: {pontos} pontos", True, CINZA)
            screen.blit(texto_placar, (largura_tela // 2 - texto_placar.get_width() // 2, 350 + i * 40))

        # Opções
        jogar_novamente = font.render("Pressione ENTER para Jogar Novamente", True, VERDE_ESCURO)
        sair = font.render("Pressione ESC para Sair", True, VERMELHO)
        screen.blit(jogar_novamente, (largura_tela // 2 - jogar_novamente.get_width() // 2, 550))
        screen.blit(sair, (largura_tela // 2 - sair.get_width() // 2, 600))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "SAIR"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    return "JOGAR_NOVAMENTE"
                elif event.key == pygame.K_ESCAPE:
                    return "SAIR"

# --- Lógica Principal do Jogo ---
def main(game_state):
    if game_state is None:
        game_state = GameState(num_players=4)
    else:
        # reiniciar estado de rodada, mas manter vitórias
        game_state.reset_rodada()

    

    game_state.distribuir_pecas()
    bots = [Bot(i, game_state) for i in range(1, 4)]
    [bot.start() for bot in bots]
    
    aguardando_escolha = False
    peca_para_escolha = None
    botao_esq_rect = pygame.Rect(largura_tela/2 - 300, altura_tela/2 - 25, 250, 50)
    botao_dir_rect = pygame.Rect(largura_tela/2 + 50, altura_tela/2 - 25, 250, 50)
    botao_passar_rect = pygame.Rect(largura_tela - 220, altura_tela - 70, 200, 50)
    clock = pygame.time.Clock()
    running = True

    while running:
        if game_state.passes_consecutivos >= game_state.num_players:
            if game_state.vencedor == -1:
                print("Empate detectado no seu turno!")
                game_state.vencedor = -2
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN and game_state.turno_atual == 0:
                with game_state.lock:
                    if aguardando_escolha:
                        if botao_esq_rect.collidepoint(event.pos):
                            executar_jogada(game_state, peca_para_escolha, 'esq', 0)
                            game_state.passar_a_vez()
                            aguardando_escolha = False
                            peca_para_escolha = None
                        elif botao_dir_rect.collidepoint(event.pos):
                            executar_jogada(game_state, peca_para_escolha, 'dir', 0)
                            game_state.passar_a_vez()
                            aguardando_escolha = False
                            peca_para_escolha = None
                    else:
                        if botao_passar_rect.collidepoint(event.pos):
                            if not jogador_tem_jogada_valida(game_state):
                                game_state.passar_a_vez()
                            else:
                                print("Você ainda pode jogar! Não pode passar a vez.")
                            continue
                        for peca_clicada in game_state.maos[0]:
                            if peca_clicada.rect and peca_clicada.rect.collidepoint(event.pos):
                                if not game_state.tabuleiro:
                                    executar_jogada(game_state, peca_clicada, 'dir', 0)
                                    game_state.passar_a_vez()
                                    break
                                
                                ponta_esq, ponta_dir = game_state.pontas
                                pode_na_esq = peca_clicada.val1 == ponta_esq or peca_clicada.val2 == ponta_esq
                                pode_na_dir = peca_clicada.val1 == ponta_dir or peca_clicada.val2 == ponta_dir
                                if pode_na_esq and pode_na_dir:
                                    aguardando_escolha = True
                                    peca_para_escolha = peca_clicada
                                elif pode_na_esq:
                                    executar_jogada(game_state, peca_clicada, 'esq', 0)
                                    game_state.passar_a_vez()
                                elif pode_na_dir:
                                    executar_jogada(game_state, peca_clicada, 'dir', 0)
                                    game_state.passar_a_vez()
                                else:
                                    print("Jogada inválida.")
                                break

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    escolha_pausa = menu_pausa()
                    if escolha_pausa == "Continuar":
                        continue
                    elif escolha_pausa == "Reiniciar":
                        main()
                        return
                    elif escolha_pausa == "Voltar ao Menu Principal":
                        escolha = menu_principal()
                        if escolha == "jogo":
                            main()
                        return

        # --- Verifica se houve vencedor e mostra tela final ---
        if game_state.vencedor != -1:
            return # Apenas retorna, o game_loop vai controlar o fluxo

        # --- Atualização da tela ---
        screen.blit(background_image, (0, 0))
        mostrar_turno_atual(game_state)
        with game_state.lock:
            desenhar_mao_jogador(game_state.maos[0])
            desenhar_maos_bots([game_state.maos[1], game_state.maos[2], game_state.maos[3]])
            desenhar_tabuleiro(game_state)
            desenhar_info(game_state)

        if (
            game_state.turno_atual == 0 and
            game_state.vencedor == -1 and
            not aguardando_escolha and
            not jogador_tem_jogada_valida(game_state)
        ):
            if jogador_tem_jogada_valida(game_state):
                pygame.draw.rect(screen, CINZA, botao_passar_rect)
                texto_botao = font.render("Passar a Vez", True, BRANCO)
                screen.blit(texto_botao, (botao_passar_rect.x + 20, botao_passar_rect.y + 10))
            else:
                game_state.passar_a_vez()

        if aguardando_escolha:
            overlay = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))
            pygame.draw.rect(screen, VERDE_ESCURO, botao_esq_rect)
            texto_esq = font.render("Jogar na Esquerda", True, BRANCO)
            screen.blit(texto_esq, (botao_esq_rect.centerx - texto_esq.get_width()/2, botao_esq_rect.centery - texto_esq.get_height()/2))
            pygame.draw.rect(screen, AZUL_ESCURO, botao_dir_rect)
            texto_dir = font.render("Jogar na Direita", True, BRANCO)
            screen.blit(texto_dir, (botao_dir_rect.centerx - texto_dir.get_width()/2, botao_dir_rect.centery - texto_dir.get_height()/2))

        pygame.display.update()
        clock.tick(30)
    def reset_rodada(self):
        self.peca_encaixada_em_bucha = False
        self.empate_anterior = False
        self.maos = [[] for _ in range(self.num_players)]
        self.tabuleiro = []
        self.pontas = [-1, -1]
        self.turno_atual = -1
        self.vencedor = -1
        self.peca_inicial_obj = None
        self.semaphores = [threading.Semaphore(0) for _ in range(self.num_players)]
        self.passes_consecutivos = 0

    pygame.quit()
    sys.exit()
    

def game_loop():
    game_state = GameState(num_players=4)

    while True: # Loop principal do jogo, controla as rodadas
        # Inicia uma nova rodada
        main(game_state) 

        # Verifica se a rodada terminou com um vencedor (ou empate)
        if game_state.vencedor != -1:
            # Verifica se há um campeão final (5+ pontos)
            campeao_id = game_state.verifica_campeao()
            if campeao_id != -1:
                # Mostra a tela de campeão e decide o que fazer depois
                escolha_final = tela_campeao_final(campeao_id, game_state.vitorias)
                if escolha_final == "JOGAR_NOVAMENTE":
                    game_state = GameState(num_players=4) # Reseta tudo para um novo jogo
                    continue # Volta para o início do loop e começa uma nova partida
                else:
                    return # Sai da função game_loop e encerra o jogo

            # Se não há campeão, mostra a tela de fim de rodada
            else:
                empate = game_state.vencedor == -2
                tela_final(empate=empate, vencedor=game_state.vencedor)
                # Adicione esta linha para resetar a rodada antes de continuar
                game_state.reset_rodada() 
        else:
            # Se a rodada não terminou (ex: usuário voltou ao menu), sai do loop
            return

if __name__ == '__main__':
    while True:
        escolha_menu = menu_principal()
        if escolha_menu == "jogo":
            game_loop() # Inicia o ciclo de jogo
        else:
            # Se o usuário escolher "Sair" no menu principal
            break 

    pygame.quit()
    sys.exit()
