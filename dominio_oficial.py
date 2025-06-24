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
        self.vitorias = [0] * num_players  # Contador de vitórias de cada jogador
        self.peca_encaixada_em_bucha = False  # Condição de encaixe dos dois lados
        self.empate_anterior = False  # Empate da partida anterior
        self.maos = [[] for _ in range(num_players)]
        self.tabuleiro = []; self.pontas = [-1, -1]
        self.turno_atual = -1; self.vencedor = -1
        self.peca_inicial_obj = None 
        self.semaphores = [threading.Semaphore(0) for _ in range(num_players)]
        self.lock = threading.Lock()

    def distribuir_pecas(self):
        todas_as_pecas = [Domino(i, j) for i in range(7) for j in range(i, 7)]
        random.shuffle(todas_as_pecas)
        for i in range(self.num_players): self.maos[i] = todas_as_pecas[i*7:(i+1)*7]
        
        maior_carroca, jogador_inicial, peca_inicial = -1, -1, None
        for i, mao in enumerate(self.maos):
            for peca in mao:
                if peca.val1 == peca.val2 and peca.val1 > maior_carroca:
                    maior_carroca, jogador_inicial, peca_inicial = peca.val1, i, peca
        
        self.turno_atual = jogador_inicial if jogador_inicial != -1 else 0
        if not peca_inicial and self.maos[self.turno_atual]:
             self.peca_inicial_obj = self.maos[self.turno_atual][0]
        else: self.peca_inicial_obj = peca_inicial

        if self.turno_atual > 0 and peca_inicial:
            with self.lock:
                executar_jogada(self, peca_inicial, 'dir', self.turno_atual)
        print(f"Jogador {self.turno_atual} começa o jogo.")
        self.semaphores[self.turno_atual].release()

    def passar_a_vez(self):
        print(f"Jogador {self.turno_atual} passou a vez.")
        self.turno_atual = (self.turno_atual + 1) % self.num_players
        self.semaphores[self.turno_atual].release()
    
    def verificar_vitoria(self, player_id):
        if not self.maos[player_id]: 
            self.vencedor = player_id
            self.contabilizar_vitoria(player_id)  # Conta a vitória
            return True
        return False
    
    def contabilizar_vitoria(self, player_id):
        """Função para contabilizar a vitória do jogador."""
        if player_id != -1:  # Se o vencedor for válido
            self.vitorias[player_id] += 1
        self.vencedor = player_id

    def exibir_vitorias(self):
        """Desenha na tela a quantidade de vitórias de cada jogador."""
        y_offset = 50
        for i in range(self.num_players):
            texto_vitoria = font.render(f"Jogador {i} - Vitórias: {self.vitorias[i]}", True, BRANCO)
            screen.blit(texto_vitoria, (10, y_offset))
            y_offset += 40
    
    def verificar_pontuacao_especial(self, peca, lado_escolhido, player_id):
        """Verifica as condições especiais e aplica pontuação extra."""
        ponta_esq, ponta_dir = self.pontas
        if peca.val1 == ponta_esq and peca.val2 == ponta_dir:
            self.peca_encaixada_em_bucha = True  # Caso encaixe de ambos os lados
            print(f"Jogador {player_id} fez um encaixe dos dois lados (bucha)!")

        if self.empate_anterior:
            print(f"Jogador {player_id} ganhou devido a um empate anterior!")
            self.empate_anterior = False  # Zera o empate após a vitória.

        if self.peca_encaixada_em_bucha:
            print(f"Pontuação especial para o jogador {player_id} devido ao encaixe de bucha.")

# --- Classe para os Bots (Threads) ---
class Bot(threading.Thread):
    def __init__(self, player_id, game_state):
        super().__init__(); self.player_id = player_id; self.game_state = game_state; self.daemon = True

    def run(self):
        while self.game_state.vencedor == -1:
            self.game_state.semaphores[self.player_id].acquire()
            if self.game_state.vencedor != -1: break
            time.sleep(random.uniform(1.0, 2.5))
            with self.game_state.lock:
                if self.game_state.turno_atual != self.player_id: continue
                
                mao_bot = self.game_state.maos[self.player_id]; ponta_esq, ponta_dir = self.game_state.pontas
                peca_a_jogar, lado_a_jogar = None, None
                for peca in mao_bot:
                    if ponta_esq == -1 or peca.val1 == ponta_esq or peca.val2 == ponta_esq:
                        peca_a_jogar, lado_a_jogar = peca, 'esq'; break
                    elif peca.val1 == ponta_dir or peca.val2 == ponta_dir:
                        peca_a_jogar, lado_a_jogar = peca, 'dir'; break
                
                if peca_a_jogar:
                    executar_jogada(self.game_state, peca_a_jogar, lado_a_jogar, self.player_id)
                else: 
                    print(f"Bot {self.player_id} passou a vez.")
                self.game_state.passar_a_vez()

# --- Funções Auxiliares e de Desenho ---
def executar_jogada(game_state, peca, lado_escolhido, player_id):
    if not game_state.tabuleiro:
        game_state.tabuleiro.append(peca)
        if not game_state.peca_inicial_obj: game_state.peca_inicial_obj = peca
        game_state.pontas = [peca.val1, peca.val2]
    else:
        ponta_esq, ponta_dir = game_state.pontas; peca.inverter_visual = False
        if lado_escolhido == 'esq':
            if peca.val1 == ponta_esq:
                peca.inverter_visual = True; game_state.pontas[0] = peca.val2
            else: game_state.pontas[0] = peca.val1
            game_state.tabuleiro.insert(0, peca)
        elif lado_escolhido == 'dir':
            if peca.val2 == ponta_dir:
                peca.inverter_visual = True; game_state.pontas[1] = peca.val1
            else: game_state.pontas[1] = peca.val2
            game_state.tabuleiro.append(peca)

    print(f"Jogador {player_id} jogou [{peca.val1}|{peca.val2}] na ponta {lado_escolhido}.")
    game_state.maos[player_id].remove(peca)
    game_state.verificar_vitoria(player_id)

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

def desenhar_tabuleiro(game_state):
    tabuleiro = game_state.tabuleiro
    if not tabuleiro: return

    margin = 150; pecas_desenhadas = []
    
    try: anchor_index = tabuleiro.index(game_state.peca_inicial_obj)
    except (ValueError, AttributeError): anchor_index = 0
    anchor_peca = tabuleiro[anchor_index]

    is_double = anchor_peca.val1 == anchor_peca.val2
    img_anchor = anchor_peca.imagem if is_double else pygame.transform.rotate(anchor_peca.imagem, 90)
    rect_anchor = img_anchor.get_rect(center=(largura_tela / 2, altura_tela / 2))
    pecas_desenhadas.append({'img': img_anchor, 'rect': rect_anchor})

    def desenhar_corrente(pecas, p_conexao_inicial, direcao_inicial, lado):
        ponto_conexao = p_conexao_inicial; direcao = direcao_inicial
        
        for peca in pecas:
            is_double = peca.val1 == peca.val2
            img = peca.imagem
            if is_double: img = pygame.transform.rotate(img, 90 if direcao[1] != 0 else 0)
            else:
                img = pygame.transform.rotate(img, 0 if direcao[1] != 0 else 90)
                if peca.inverter_visual:
                    flip_x = (direcao == (1, 0) or direcao == (-1, 0))
                    flip_y = (direcao == (0, 1) or direcao == (0, -1))
                    img = pygame.transform.flip(img, flip_x, flip_y)

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
                direcao = nova_direcao
                if is_double: img = pygame.transform.rotate(peca.imagem, 90 if direcao[1] != 0 else 0)
                else: img = pygame.transform.rotate(peca.imagem, 0 if direcao[1] != 0 else 90)
                if peca.inverter_visual:
                    flip_x = (direcao == (1, 0) or direcao == (-1, 0))
                    flip_y = (direcao == (0, 1) or direcao == (0, -1))
                    img = pygame.transform.flip(img, flip_x, flip_y)

                rect = img.get_rect()
                if direcao == (0, 1): rect.midtop = ponto_conexao
                elif direcao in [(-1, 0), (1,0)]:
                     if lado == 'dir': rect.midright = ponto_conexao
                     else: rect.midleft = ponto_conexao

            pecas_desenhadas.append({'img': img, 'rect': rect})
            if direcao == (1, 0): ponto_conexao = rect.midright
            elif direcao == (-1, 0): ponto_conexao = rect.midleft
            elif direcao == (0, 1): ponto_conexao = rect.midbottom

    desenhar_corrente(tabuleiro[anchor_index+1:], rect_anchor.midright, (1,0), 'dir')
    desenhar_corrente(reversed(tabuleiro[:anchor_index]), rect_anchor.midleft, (-1,0), 'esq')

    for p in pecas_desenhadas: screen.blit(p['img'], p['rect'])

def desenhar_info(game_state):
    if game_state.vencedor != -1:
        msg = "Você Venceu!" if game_state.vencedor == 0 else f"Bot {game_state.vencedor} Venceu!"
        cor = AMARELO if game_state.vencedor == 0 else VERMELHO
        texto_vencedor = font_grande.render(msg, True, cor)
        screen.blit(texto_vencedor, (largura_tela/2 - texto_vencedor.get_width()/2, altura_tela/2 - 100))
    elif game_state.turno_atual == 0:
        texto_turno = font.render("Sua vez de jogar!", True, BRANCO)
        screen.blit(texto_turno, (largura_tela / 2 - texto_turno.get_width() / 2, altura_tela - 250))

    game_state.exibir_vitorias()
# --- Lógica Principal do Jogo ---
def main():
    game_state = GameState(num_players=4); game_state.distribuir_pecas()
    bots = [Bot(i, game_state) for i in range(1, 4)]; [bot.start() for bot in bots]
    
    aguardando_escolha = False; peca_para_escolha = None
    peca_para_escolha = None
    botao_esq_rect = pygame.Rect(largura_tela/2 - 300, altura_tela/2 - 25, 250, 50)
    botao_dir_rect = pygame.Rect(largura_tela/2 + 50, altura_tela/2 - 25, 250, 50)
    botao_passar_rect = pygame.Rect(largura_tela - 220, altura_tela - 70, 200, 50)
    clock = pygame.time.Clock(); 
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if game_state.vencedor != -1: continue

            if event.type == pygame.MOUSEBUTTONDOWN and game_state.turno_atual == 0:
                with game_state.lock:
                    if aguardando_escolha:
                        if botao_esq_rect.collidepoint(event.pos):
                            executar_jogada(game_state, peca_para_escolha, 'esq', 0); game_state.passar_a_vez()
                            aguardando_escolha = False; peca_para_escolha = None
                        elif botao_dir_rect.collidepoint(event.pos):
                            executar_jogada(game_state, peca_para_escolha, 'dir', 0); game_state.passar_a_vez()
                            aguardando_escolha = False; peca_para_escolha = None
                    else:
                        if botao_passar_rect.collidepoint(event.pos):
                            game_state.passar_a_vez(); continue
                        for peca_clicada in game_state.maos[0]:
                            if peca_clicada.rect and peca_clicada.rect.collidepoint(event.pos):
                                if not game_state.tabuleiro:
                                    executar_jogada(game_state, peca_clicada, 'dir', 0); game_state.passar_a_vez()
                                    break
                                
                                ponta_esq, ponta_dir = game_state.pontas
                                pode_na_esq = peca_clicada.val1 == ponta_esq or peca_clicada.val2 == ponta_esq
                                pode_na_dir = peca_clicada.val1 == ponta_dir or peca_clicada.val2 == ponta_dir
                                if pode_na_esq and pode_na_dir:
                                    aguardando_escolha = True; peca_para_escolha = peca_clicada
                                elif pode_na_esq: 
                                    executar_jogada(game_state, peca_clicada, 'esq', 0); game_state.passar_a_vez()
                                elif pode_na_dir: 
                                    executar_jogada(game_state, peca_clicada, 'dir', 0); game_state.passar_a_vez()
                                else: print("Jogada inválida.")
                                break 
        
        screen.blit(background_image, (0, 0))
        with game_state.lock:
            desenhar_mao_jogador(game_state.maos[0])
            desenhar_maos_bots([game_state.maos[1], game_state.maos[2], game_state.maos[3]])
            desenhar_tabuleiro(game_state)
            desenhar_info(game_state)
        
        if game_state.turno_atual == 0 and game_state.vencedor == -1 and not aguardando_escolha:
            pygame.draw.rect(screen, CINZA, botao_passar_rect)
            texto_botao = font.render("Passar a Vez", True, BRANCO)
            screen.blit(texto_botao, (botao_passar_rect.x + 20, botao_passar_rect.y + 10))
        
        if aguardando_escolha:
            overlay = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA); overlay.fill((0, 0, 0, 180)); screen.blit(overlay, (0, 0))
            pygame.draw.rect(screen, VERDE_ESCURO, botao_esq_rect); texto_esq = font.render("Jogar na Esquerda", True, BRANCO); screen.blit(texto_esq, (botao_esq_rect.centerx - texto_esq.get_width()/2, botao_esq_rect.centery - texto_esq.get_height()/2))
            pygame.draw.rect(screen, AZUL_ESCURO, botao_dir_rect); texto_dir = font.render("Jogar na Direita", True, BRANCO); screen.blit(texto_dir, (botao_dir_rect.centerx - texto_dir.get_width()/2, botao_dir_rect.centery - texto_dir.get_height()/2))

        pygame.display.update()
        clock.tick(30)
        
    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()