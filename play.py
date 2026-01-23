import sys
import traceback
from pathlib import Path

# Tenta importar as bibliotecas e avisa se falhar
try:
    import pygame
    import json
except ImportError as e:
    print(f"\n[ERRO CRITICO] Falta biblioteca: {e}")
    print("Execute: pip install pygame-ce")
    input("Pressione ENTER para sair...")
    sys.exit()

# Configurações Iniciais
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
TILE_SIZE = 64
FPS = 60

# Cores
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
BLUE = (0, 0, 255)

class Game:
    def __init__(self):
        print("[DEBUG] Inicializando Pygame...")
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("O Mundo de Pandorha - Modo de Teste")
        self.font = pygame.font.SysFont("Arial", 24) # Fonte para o texto
        self.clock = pygame.time.Clock()
        self.running = True
        # Permite segurar a tecla para andar repetidamente (delay inicial, intervalo)
        pygame.key.set_repeat(200, 100)
        
        # Câmera (deslocamento)
        self.camera_x = 0
        self.camera_y = 0
        
        # Jogador
        # Inicia alinhado ao grid (coluna 2, linha 2) e com o tamanho exato do tile (64x64)
        start_pos = 2 * TILE_SIZE
        self.player_rect = pygame.Rect(start_pos, start_pos, TILE_SIZE, TILE_SIZE)
        self.player_hp = 100
        self.player_attack_power = 10
        
        # Dados do Mapa
        self.current_dialogue = None # Texto atual sendo exibido (None se não houver)
        self.map_data = None
        self.tiles_images = {}
        self.collision_layer = [] # Lista de retângulos de colisão
        self.npcs = [] # Lista de NPCs carregados
        
        print("[DEBUG] Carregando Assets...")
        self.load_assets()
        
        print("[DEBUG] Selecionando Mapa...")
        map_file = self.select_map_file()
        if map_file:
            print(f"[DEBUG] Carregando Mapa: {map_file}...")
            self.load_map(map_file)
        else:
            print("[AVISO] Nenhum mapa selecionado. O jogo iniciará vazio ou fechará.")
            self.running = False

    def select_map_file(self):
        """Abre uma janela para o usuário escolher o arquivo .json"""
        try:
            import tkinter as tk
            from tkinter import filedialog
            
            # Cria uma janela invisível do tkinter apenas para abrir o diálogo
            root = tk.Tk()
            root.withdraw() 
            
            file_path = filedialog.askopenfilename(
                title="Selecione o Mapa para Jogar",
                filetypes=[("Mapas JSON", "*.json"), ("Todos os arquivos", "*.*")],
                initialdir=str(Path.cwd())
            )
            root.destroy()
            return file_path
        except Exception as e:
            print(f"[ERRO] Falha ao abrir seletor de arquivos: {e}")
            return "novo_mapa.json" # Tenta o padrão em caso de erro

    def load_assets(self):
        """Carrega as imagens dos sprites"""
        sprite_path = Path("assets/sprites")
        if not sprite_path.is_dir():
            print("ERRO: Pasta de sprites não encontrada!")
            return

        # Mapeia ID -> Imagem Pygame
        # Nota: O Editor usa IDs baseados na ordem alfabética. Precisamos replicar isso.
        sprite_files = sorted(list(sprite_path.glob("*.webp")))
        
        # ID 0 é vazio
        current_id = 1
        for file in sprite_files:
            try:
                img = pygame.image.load(file).convert_alpha()
                img = pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
                self.tiles_images[current_id] = img
                current_id += 1
            except Exception as e:
                print(f"Erro ao carregar {file}: {e}")

    def load_map(self, filename):
        """Carrega o JSON do mapa e prepara as colisões"""
        if not Path(filename).exists():
            print(f"Mapa {filename} não encontrado.")
            return

        with open(filename, 'r') as f:
            data = json.load(f)
            
        # Suporte ao formato novo
        if isinstance(data, dict):
            self.map_data = data.get("tiles", [])
            self.npcs = data.get("npcs", []) # Carrega a lista de NPCs
        else:
            self.map_data = data

        # Processar Colisões (Camada 6 no índice 0-based, ou seja, a 7ª camada)
        # Lembre-se: LAYER_NAMES[6] é "7. Colisao (Dados)"
        if len(self.map_data) > 6:
            layer_colisao = self.map_data[6]
            for row_idx, row in enumerate(layer_colisao):
                for col_idx, tile_id in enumerate(row):
                    if tile_id != 0: # Se tem algo na camada de colisão
                        # Cria um retângulo de bloqueio
                        rect = pygame.Rect(col_idx * TILE_SIZE, row_idx * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                        self.collision_layer.append(rect)
        
        print(f"Mapa carregado! {len(self.collision_layer)} blocos de colisão encontrados.")

    def move_player(self, dx, dy):
        """Move o jogador uma quantidade fixa e verifica colisão"""
        # Movimento no eixo X
        if dx != 0:
            self.player_rect.x += dx
            self.check_collision(dx, 0)
        
        # Movimento no eixo Y
        if dy != 0:
            self.player_rect.y += dy
            self.check_collision(0, dy)
            
    def interact(self):
        """Tenta interagir com um NPC adjacente"""
        # Se já tem dialogo aberto, fecha
        if self.current_dialogue:
            self.current_dialogue = None
            return

        # Verifica os 4 vizinhos
        # Cria retângulos temporários ao redor do jogador para checar colisão com NPCs
        neighbors = [
            pygame.Rect(self.player_rect.x, self.player_rect.y - TILE_SIZE, TILE_SIZE, TILE_SIZE), # Cima
            pygame.Rect(self.player_rect.x, self.player_rect.y + TILE_SIZE, TILE_SIZE, TILE_SIZE), # Baixo
            pygame.Rect(self.player_rect.x - TILE_SIZE, self.player_rect.y, TILE_SIZE, TILE_SIZE), # Esquerda
            pygame.Rect(self.player_rect.x + TILE_SIZE, self.player_rect.y, TILE_SIZE, TILE_SIZE)  # Direita
        ]
        
        for npc in self.npcs:
            npc_rect = pygame.Rect(npc["x"], npc["y"], TILE_SIZE, TILE_SIZE)
            for neighbor in neighbors:
                if neighbor.colliderect(npc_rect):
                    self.current_dialogue = npc.get("dialogue", "...")
                    return # Encontrou um, para de procurar

    def attack(self):
        """Ataca um NPC adjacente"""
        # Verifica os 4 vizinhos (quem está grudado no jogador)
        neighbors = [
            pygame.Rect(self.player_rect.x, self.player_rect.y - TILE_SIZE, TILE_SIZE, TILE_SIZE),
            pygame.Rect(self.player_rect.x, self.player_rect.y + TILE_SIZE, TILE_SIZE, TILE_SIZE),
            pygame.Rect(self.player_rect.x - TILE_SIZE, self.player_rect.y, TILE_SIZE, TILE_SIZE),
            pygame.Rect(self.player_rect.x + TILE_SIZE, self.player_rect.y, TILE_SIZE, TILE_SIZE)
        ]
        
        target_npc = None
        for npc in self.npcs:
            npc_rect = pygame.Rect(npc["x"], npc["y"], TILE_SIZE, TILE_SIZE)
            for neighbor in neighbors:
                if neighbor.colliderect(npc_rect):
                    target_npc = npc
                    break
            if target_npc: break
        
        if target_npc:
            # Causa dano
            dmg = self.player_attack_power
            target_npc["hp"] = target_npc.get("hp", 10) - dmg
            print(f"Voce atacou {target_npc['name']}! Dano: {dmg}. Vida restante: {target_npc['hp']}")
            
            if target_npc["hp"] <= 0:
                print(f"{target_npc['name']} foi derrotado!")
                self.npcs.remove(target_npc)
            else:
                # Revide do NPC
                npc_dmg = target_npc.get("attack", 2)
                self.player_hp -= npc_dmg
                print(f"{target_npc['name']} revidou! Voce tomou {npc_dmg} de dano. Sua vida: {self.player_hp}")

    def check_collision(self, dx, dy):
        """Verifica colisão com as paredes e empurra o jogador de volta"""
        for wall in self.collision_layer:
            if self.player_rect.colliderect(wall):
                if dx > 0: # Indo para direita
                    self.player_rect.right = wall.left
                if dx < 0: # Indo para esquerda
                    self.player_rect.left = wall.right
                if dy > 0: # Indo para baixo
                    self.player_rect.bottom = wall.top
                if dy < 0: # Indo para cima
                    self.player_rect.top = wall.bottom

    def update_camera(self):
        # Centraliza a câmera no jogador
        target_x = self.player_rect.centerx - SCREEN_WIDTH // 2
        target_y = self.player_rect.centery - SCREEN_HEIGHT // 2
        
        # Interpolação suave (opcional, aqui é direto)
        self.camera_x = target_x
        self.camera_y = target_y

    def draw(self):
        self.screen.fill(BLACK)
        
        # Desenha o Mapa (Apenas camadas visuais 0, 1, 2)
        if self.map_data:
            # Desenhamos apenas o que está visível na tela para otimizar
            start_col = int(self.camera_x // TILE_SIZE)
            end_col = start_col + (SCREEN_WIDTH // TILE_SIZE) + 2
            start_row = int(self.camera_y // TILE_SIZE)
            end_row = start_row + (SCREEN_HEIGHT // TILE_SIZE) + 2
            
            # Limites do grid
            # (Assumindo tamanho fixo do grid por enquanto, idealmente pegar do len(map_data[0]))
            
            for layer_idx in [0, 1, 2]: # Camadas visuais
                layer = self.map_data[layer_idx]
                for row in range(max(0, start_row), min(len(layer), end_row)):
                    for col in range(max(0, start_col), min(len(layer[0]), end_col)):
                        tile_id = layer[row][col]
                        if tile_id != 0 and tile_id in self.tiles_images:
                            pos_x = (col * TILE_SIZE) - self.camera_x
                            pos_y = (row * TILE_SIZE) - self.camera_y
                            self.screen.blit(self.tiles_images[tile_id], (pos_x, pos_y))

        # Desenha o Jogador (Quadrado Branco)
        player_screen_pos = (self.player_rect.x - self.camera_x, self.player_rect.y - self.camera_y)
        pygame.draw.rect(self.screen, WHITE, (*player_screen_pos, self.player_rect.width, self.player_rect.height))
        
        # Desenha os NPCs
        for npc in self.npcs:
            npc_x = npc.get("x", 0) - self.camera_x
            npc_y = npc.get("y", 0) - self.camera_y
            sprite_id = npc.get("sprite_id", 1)
            
            # Desenha o sprite do NPC se existir
            if sprite_id in self.tiles_images:
                self.screen.blit(self.tiles_images[sprite_id], (npc_x, npc_y))
            else:
                # Fallback: quadrado vermelho se não achar imagem
                pygame.draw.rect(self.screen, RED, (npc_x, npc_y, TILE_SIZE, TILE_SIZE))
            
            # (Opcional) Desenhar nome ou barra de vida aqui depois

        # Debug: Desenha colisões (ATIVADO PARA TESTE)
        for wall in self.collision_layer:
            wall_screen = (wall.x - self.camera_x, wall.y - self.camera_y, wall.width, wall.height)
            pygame.draw.rect(self.screen, (255, 0, 0), wall_screen, 2)
            
        # Desenha a Interface de Diálogo (se houver)
        if self.current_dialogue:
            # Caixa de fundo
            dialogue_box = pygame.Rect(50, SCREEN_HEIGHT - 150, SCREEN_WIDTH - 100, 130)
            pygame.draw.rect(self.screen, BLACK, dialogue_box)
            pygame.draw.rect(self.screen, WHITE, dialogue_box, 2) # Borda branca
            
            # Texto
            text_surface = self.font.render(self.current_dialogue, True, WHITE)
            self.screen.blit(text_surface, (70, SCREEN_HEIGHT - 130))
            
        # HUD: Vida do Jogador
        hp_text = f"HP: {self.player_hp}"
        hp_surface = self.font.render(hp_text, True, RED if self.player_hp < 30 else WHITE)
        self.screen.blit(hp_surface, (10, 10))

        pygame.display.flip()

    def run(self):
        while self.running:
            self.clock.tick(FPS)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    
                    # Interação (Espaço ou E)
                    if event.key == pygame.K_SPACE or event.key == pygame.K_e:
                        self.interact()
                        
                    # Combate (K)
                    if event.key == pygame.K_k:
                        self.attack()
                    
                    # Movimento Quadrado a Quadrado (Grid-based)
                    if event.key == pygame.K_w or event.key == pygame.K_UP:
                        self.move_player(0, -TILE_SIZE)
                    elif event.key == pygame.K_s or event.key == pygame.K_DOWN:
                        self.move_player(0, TILE_SIZE)
                    elif event.key == pygame.K_a or event.key == pygame.K_LEFT:
                        self.move_player(-TILE_SIZE, 0)
                    elif event.key == pygame.K_d or event.key == pygame.K_RIGHT:
                        self.move_player(TILE_SIZE, 0)

            self.update_camera()
            self.draw()

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    try:
        print("--- INICIANDO MODO DE TESTE ---")
        Game().run()
    except Exception as e:
        print("\n[ERRO FATAL] O jogo quebrou!")
        traceback.print_exc() # Imprime o erro detalhado
        input("\nPressione ENTER para fechar a janela de erro...")
