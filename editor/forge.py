import dearpygui.dearpygui as dpg
import json
from pathlib import Path
from PIL import Image
import sys

# Garante que o terminal possa exibir caracteres especiais corretamente
sys.stdout.reconfigure(encoding='utf-8')

# --- DADOS E ESTADO DO EDITOR ---

# O tamanho do nosso tile (agora 64x64)
TILE_SIZE_PX = 64

# Dimensões do nosso grid do mapa (ajustadas para caber mais ou menos na mesma área)
GRID_WIDTH_CELLS = 13
GRID_HEIGHT_CELLS = 9
NUM_LAYERS = 7
# 0=Chão, 1=Objetos, 2=Topo (Visuais)
# 3=Som, 4=Luz, 5=Cheiro (Dados)
# 6=Colisão (Dados)

LAYER_NAMES = [
    "1. Chao (Visual)", "2. Objetos (Visual)", "3. Topo (Visual)",
    "4. Sons (Dados)", "5. Luzes (Dados)", "6. Cheiros (Dados)",
    "7. Colisao (Dados)"
]

# O dicionário de TILES agora será preenchido dinamicamente
TILES = {}
# O registro de texturas também será preenchido dinamicamente
TEXTURE_REGISTRY = {}

# Estado atual do editor
editor_state = {
    "selected_tile_id": 0,  # Usaremos o ID 0 como padrão
    "current_layer": 0,     # Começa editando a camada 0 (Chão)
    "view_mode": "Ver Todas", # Modos: "Ver Todas", "Apenas Atual", "Atual + Anterior"
    "camera": {"x": 0.0, "y": 0.0, "zoom": 1.0}, # Posição X, Y e Zoom da câmera
    "drag_ref": [0, 0], # Memória para calcular o movimento do mouse manualmente
    "interaction_mode": None, # "painting" ou "dragging_npc"
    "selected_npc_index": None # Índice do NPC selecionado na lista npc_data
}

# Estrutura de dados que guarda o mapa (Agora com camadas!)
# É uma lista de 3 grids. map_data[0] é o chão, map_data[1] objetos, etc.
map_data = [
    [[0 for _ in range(GRID_WIDTH_CELLS)] for _ in range(GRID_HEIGHT_CELLS)] for _ in range(NUM_LAYERS)
]

# Lista para armazenar os NPCs. Cada NPC será um dicionário: {"x": 0, "y": 0, "name": "Goblin", "sprite_id": 1}
npc_data = []

def create_system_markers(start_id):
    """Cria texturas de cor sólida para representar dados invisíveis (Luz, Som, Cheiro)"""
    global TILES, TEXTURE_REGISTRY
    
    # Definição dos marcadores de sistema
    markers = [
        # Camada 3: Sons (Azul)
        {"name": "Som: Ambiente", "color": [0.0, 0.0, 1.0, 0.6], "layer_target": 3},
        {"name": "Som: Evento", "color": [0.0, 0.5, 1.0, 0.6], "layer_target": 3},
        # Camada 4: Luzes (Amarelo/Laranja)
        {"name": "Luz: Tocha (Pequena)", "color": [1.0, 0.6, 0.0, 0.6], "layer_target": 4},
        {"name": "Luz: Sol (Area)", "color": [1.0, 1.0, 0.0, 0.4], "layer_target": 4},
        {"name": "Luz: Magica (Azul)", "color": [0.0, 1.0, 1.0, 0.6], "layer_target": 4},
        # Camada 5: Cheiros (Verde/Roxo)
        {"name": "Cheiro: Natureza", "color": [0.0, 1.0, 0.0, 0.5], "layer_target": 5},
        {"name": "Cheiro: Podre", "color": [0.5, 0.0, 0.5, 0.5], "layer_target": 5},
        # Camada 6: Colisão (Vermelho)
        {"name": "Colisao: Bloqueio", "color": [1.0, 0.0, 0.0, 0.5], "layer_target": 6},
    ]

    current_id = start_id
    for m in markers:
        # Cria uma textura 64x64 de cor sólida
        texture_data = m["color"] * (TILE_SIZE_PX * TILE_SIZE_PX)
        
        texture_tag = dpg.add_static_texture(
            TILE_SIZE_PX, TILE_SIZE_PX, texture_data, parent="texture_container"
        )
        
        TEXTURE_REGISTRY[current_id] = texture_tag
        TILES[current_id] = {
            "name": m["name"], 
            "texture_tag": texture_tag, 
            "layer_target": m["layer_target"] # Indica em qual camada esse tile deve ser usado
        }
        current_id += 1

def load_and_register_sprites():
    """
    Escaneia a pasta 'assets/sprites', carrega as imagens .webp,
    as registra como texturas no DPG e preenche o dicionário TILES.
    """
    global TILES, TEXTURE_REGISTRY
    TILES.clear()
    TEXTURE_REGISTRY.clear()

    sprite_path = Path("assets/sprites")
    if not sprite_path.is_dir():
        print(f"Aviso: Diretório de sprites '{sprite_path}' não encontrado.")
        return

    # Usaremos um ID numérico incremental para cada tile
    tile_id_counter = 0

    # Adiciona um tile "Vazio" (ID 0) por padrão
    TILES[0] = {"name": "Vazio", "texture_tag": None, "layer_target": -1}
    tile_id_counter += 1

    # Busca por todos os arquivos .webp
    sprite_files = sorted(list(sprite_path.glob("*.webp")))

    for webp_path in sprite_files:
        try:
            with Image.open(webp_path) as img:
                # Converte a imagem para RGBA, que é o que o DPG espera
                img_rgba = img.convert("RGBA")
                width, height = img.size
                
                # Normaliza os dados para floats (0.0 a 1.0) para garantir que as cores apareçam
                # Isso corrige o problema das imagens ficarem brancas
                raw_data = img_rgba.tobytes()
                texture_data = [x / 255.0 for x in raw_data]

            # Registra a textura estática (mais estável para sprites que não mudam)
            texture_tag = dpg.add_static_texture(
                width,
                height,
                texture_data,
                parent="texture_container"
            )
            
            # Guarda a tag da textura para referência futura
            TEXTURE_REGISTRY[tile_id_counter] = texture_tag

            # Adiciona a informação do tile ao nosso dicionário
            tile_name = webp_path.stem.replace("_", " ").title() # Ex: "grass_tile" -> "Grass Tile"
            TILES[tile_id_counter] = {
                "name": tile_name, 
                "texture_tag": texture_tag,
                "layer_target": 0 # Por padrão, sprites vão para camadas visuais (0, 1, 2)
            }
            
            print(f"Carregado Sprite: '{tile_name}' (ID: {tile_id_counter})")
            tile_id_counter += 1

        except Exception as e:
            print(f"Erro ao carregar o sprite '{webp_path.name}': {e}")
            
    # Cria os marcadores de sistema (Luz, Som, etc) após os sprites
    create_system_markers(tile_id_counter)

    # Define o tile selecionado inicial como o primeiro tile carregado (se houver)
    if len(TILES) > 1:
        editor_state["selected_tile_id"] = 1 # Pula o "Vazio"
    else:
        editor_state["selected_tile_id"] = 0


# --- FUNÇÕES DE CALLBACK (Ações) ---

def _save_map_callback(sender, app_data):
    global map_data, npc_data
    file_path_name = app_data['file_path_name']
    print(f"Salvando mapa em: {file_path_name}")
    
    # Estrutura completa do arquivo de mapa
    save_data = {
        "version": "1.0",
        "tiles": map_data,
        "npcs": npc_data
    }
    
    try:
        with open(file_path_name, 'w') as f:
            json.dump(save_data, f, indent=4)
        print("Mapa salvo com sucesso!")
    except Exception as e:
        print(f"Ocorreu um erro ao salvar o mapa: {e}")

def _load_map_callback(sender, app_data):
    global map_data, npc_data
    file_path_name = app_data['file_path_name']
    print(f"Carregando mapa de: {file_path_name}")
    try:
        with open(file_path_name, 'r') as f:
            loaded_data = json.load(f)
            
            # CASO 1: Formato Novo (Dicionário com versão)
            if isinstance(loaded_data, dict) and "tiles" in loaded_data:
                map_data = loaded_data["tiles"]
                npc_data = loaded_data.get("npcs", [])
                print("Mapa (Formato V1.0) carregado com sucesso!")
                
                # Garante compatibilidade de camadas se o mapa for antigo
                while len(map_data) < NUM_LAYERS:
                    map_data.append([[0] * GRID_WIDTH_CELLS for _ in range(GRID_HEIGHT_CELLS)])
                
                redraw_map("map_drawlist")
                return

            # CASO 2: Formato Intermediário (Lista de Camadas)
            # Verifica se é um mapa novo (com camadas) ou antigo (sem camadas)
            # Se o primeiro item for uma lista de listas, é o formato novo (3D)
            if isinstance(loaded_data, list) and isinstance(loaded_data[0][0], list):
                map_data = loaded_data
                npc_data = [] # Limpa NPCs pois formato antigo não tinha
                print("Mapa (com camadas) carregado com sucesso!")
                
                # Se o mapa carregado tiver menos camadas que o editor atual (ex: mapa antigo de 3 camadas), expande
                while len(map_data) < NUM_LAYERS:
                    map_data.append([[0] * GRID_WIDTH_CELLS for _ in range(GRID_HEIGHT_CELLS)])
                
                redraw_map("map_drawlist")
            
            # CASO 3: Formato Antigo (Apenas 1 Grid 2D)
            elif isinstance(loaded_data, list) and len(loaded_data) == GRID_HEIGHT_CELLS:
                map_data = [loaded_data] + [[[0] * GRID_WIDTH_CELLS for _ in range(GRID_HEIGHT_CELLS)] for _ in range(NUM_LAYERS - 1)]
                npc_data = []
                print("Mapa antigo convertido e carregado!")
                redraw_map("map_drawlist")
            else:
                print("Erro: O arquivo de mapa parece ter dimensões inválidas.")

    except Exception as e:
        print(f"Ocorreu um erro ao carregar o mapa: {e}")

def select_tile(sender, app_data, user_data):
    tile_id = user_data
    editor_state["selected_tile_id"] = tile_id
    dpg.set_value("selected_tile_text", f"Selecionado: {TILES[tile_id]['name']}")

def change_layer(sender, app_data):
    # O app_data vem como string do Radio Button (ex: "Camada 1 (Chão)")
    # Vamos pegar o primeiro caractere numérico da string
    if app_data and app_data[0].isdigit():
        layer = int(app_data[0]) - 1 # "1..." vira 0
    else: layer = 0
    
    editor_state["current_layer"] = layer
    refresh_palette() # Atualiza a lista visualmente quando a camada muda
    redraw_map("map_drawlist") # Redesenha o mapa caso o modo de visualização dependa da camada atual

def change_view_mode(sender, app_data):
    editor_state["view_mode"] = app_data
    redraw_map("map_drawlist")

def reset_camera_callback(sender, app_data):
    editor_state["camera"] = {"x": 0.0, "y": 0.0, "zoom": 1.0}
    print("Camera resetada para o centro.")
    redraw_map("map_drawlist")

def map_mouse_release_callback(sender, app_data):
    # Quando soltar o botão direito, resetamos a referência de movimento
    editor_state["drag_ref"] = [0, 0]

def map_mouse_release_left_callback(sender, app_data):
    # Quando soltar o botão esquerdo, paramos de pintar ou arrastar NPC
    editor_state["interaction_mode"] = None

def map_drag_callback(sender, app_data):
    # app_data vem como [button, dx, dy]
    # O DPG acumula o valor (ex: 1, 2, 3, 4...).
    # Para mover suavemente, precisamos subtrair o valor anterior (4 - 3 = 1)
    
    current_dx = app_data[1]
    current_dy = app_data[2]
    
    step_x = current_dx - editor_state["drag_ref"][0]
    step_y = current_dy - editor_state["drag_ref"][1]
    
    editor_state["camera"]["x"] += step_x
    editor_state["camera"]["y"] += step_y
    
    editor_state["drag_ref"] = [current_dx, current_dy]
    redraw_map("map_drawlist")

def map_zoom_callback(sender, app_data):
    # app_data no scroll é o valor da rolagem (positivo ou negativo)
    zoom_speed = 0.1
    current_zoom = editor_state["camera"]["zoom"]
    
    if app_data > 0:
        new_zoom = current_zoom + zoom_speed
    else:
        new_zoom = current_zoom - zoom_speed
    
    # Limita o zoom entre 0.1 (muito longe) e 3.0 (muito perto)
    new_zoom = max(0.1, min(new_zoom, 3.0))
    
    editor_state["camera"]["zoom"] = new_zoom
    redraw_map("map_drawlist")

def paint_on_map_callback(sender, app_data):
    # Esta função é chamada enquanto o botão esquerdo está pressionado (mouse down)

    if dpg.is_item_hovered("map_drawlist"):
        mouse_pos = dpg.get_drawing_mouse_pos()
        
        # Converte a posição do mouse (Tela) para o Grid (Mundo)
        cam = editor_state["camera"]
        world_x = (mouse_pos[0] - cam["x"]) / cam["zoom"]
        world_y = (mouse_pos[1] - cam["y"]) / cam["zoom"]

        # LÓGICA DE CLIQUE INICIAL (Detectado pelo estado None quando o mouse está pressionado)
        if editor_state["interaction_mode"] is None:
            # 1. Verifica se clicou em cima de um NPC
            clicked_npc_index = None
            # Checamos de trás para frente para pegar o que está "por cima" visualmente
            for i in range(len(npc_data) - 1, -1, -1):
                npc = npc_data[i]
                # Colisão Retangular (AABB) - Verifica se o mouse está dentro do quadrado do NPC
                if (npc["x"] <= world_x <= npc["x"] + TILE_SIZE_PX) and \
                   (npc["y"] <= world_y <= npc["y"] + TILE_SIZE_PX):
                    clicked_npc_index = i
                    break
            
            if clicked_npc_index is not None:
                # MODO ARRASTAR NPC
                editor_state["interaction_mode"] = "dragging_npc"
                editor_state["selected_npc_index"] = clicked_npc_index
                
                # Atualiza a UI com os dados do NPC clicado
                npc = npc_data[clicked_npc_index]
                dpg.set_value("input_npc_name", npc["name"])
                sprite_id = npc.get("sprite_id", 1)
                if sprite_id in TILES:
                    dpg.set_value("input_npc_sprite", f"{sprite_id}: {TILES[sprite_id]['name']}")
                dpg.set_value("input_npc_hp", npc.get("hp", 10))
                dpg.set_value("input_npc_attack", npc.get("attack", 2))
                print(f"NPC Selecionado: {npc['name']}")
            else:
                # MODO PINTAR
                editor_state["interaction_mode"] = "painting"

        # LÓGICA DE ARRASTAR / PINTAR (Executa enquanto segura)
        if editor_state.get("interaction_mode") == "dragging_npc":
            idx = editor_state["selected_npc_index"]
            if idx is not None and idx < len(npc_data):
                # Alinha ao grid (Snap to Grid)
                # Calcula a coluna e linha baseada na posição do mouse
                col = int(world_x / TILE_SIZE_PX)
                row = int(world_y / TILE_SIZE_PX)
                npc_data[idx]["x"] = col * TILE_SIZE_PX
                npc_data[idx]["y"] = row * TILE_SIZE_PX
                redraw_map("map_drawlist")
                
        elif editor_state.get("interaction_mode") == "painting":
            col = int(world_x / TILE_SIZE_PX)
            row = int(world_y / TILE_SIZE_PX)

            if 0 <= row < GRID_HEIGHT_CELLS and 0 <= col < GRID_WIDTH_CELLS:
                layer = editor_state["current_layer"]
                if map_data[layer][row][col] != editor_state["selected_tile_id"]:
                    map_data[layer][row][col] = editor_state["selected_tile_id"]
                    redraw_map("map_drawlist")

# --- FUNÇÕES DE GERENCIAMENTO DE NPCS ---

def refresh_npc_list():
    """Atualiza a lista visual de NPCs na janela de gerenciamento"""
    if not dpg.does_item_exist("list_npcs"):
        return
        
    dpg.delete_item("list_npcs", children_only=True)
    
    for i, npc in enumerate(npc_data):
        with dpg.group(horizontal=True, parent="list_npcs"):
            dpg.add_button(label="X", callback=delete_npc_callback, user_data=i)
            dpg.add_text(f"{npc['name']} (Sprite ID: {npc.get('sprite_id', '?')})")

def add_npc_callback(sender, app_data):
    # Pega os dados dos campos
    name = dpg.get_value("input_npc_name")
    sprite_str = dpg.get_value("input_npc_sprite")
    hp = dpg.get_value("input_npc_hp")
    attack = dpg.get_value("input_npc_attack")
    
    if not name or not sprite_str:
        print("Erro: Nome ou Sprite inválidos.")
        return

    # Extrai o ID do sprite da string "ID: Nome"
    try:
        sprite_id = int(sprite_str.split(":")[0])
    except:
        sprite_id = 1

    # Define a posição inicial baseada no centro da câmera
    cam = editor_state["camera"]
    # O centro da tela (assumindo viewport 1280x720) mais a posição da câmera
    start_x = cam["x"] + (600 / cam["zoom"]) # Aproximação do centro
    start_y = cam["y"] + (300 / cam["zoom"])

    new_npc = {
        "name": name,
        "sprite_id": sprite_id,
        "x": int(start_x),
        "y": int(start_y),
        "hp": int(hp),
        "attack": int(attack)
    }
    
    npc_data.append(new_npc)
    print(f"NPC Adicionado: {new_npc}")
    
    refresh_npc_list()
    redraw_map("map_drawlist")

def save_npc_callback(sender, app_data):
    idx = editor_state.get("selected_npc_index")
    if idx is None or idx >= len(npc_data):
        print("Nenhum NPC selecionado para salvar.")
        return

    name = dpg.get_value("input_npc_name")
    sprite_str = dpg.get_value("input_npc_sprite")
    hp = dpg.get_value("input_npc_hp")
    attack = dpg.get_value("input_npc_attack")
    
    try:
        sprite_id = int(sprite_str.split(":")[0])
    except:
        sprite_id = 1
        
    npc_data[idx]["name"] = name
    npc_data[idx]["sprite_id"] = sprite_id
    npc_data[idx]["hp"] = int(hp)
    npc_data[idx]["attack"] = int(attack)
    print(f"NPC Atualizado: {name} | HP: {hp} | ATK: {attack}")
    refresh_npc_list()
    redraw_map("map_drawlist")

def delete_npc_callback(sender, app_data, user_data):
    # user_data é o índice na lista
    index = user_data
    if 0 <= index < len(npc_data):
        removed = npc_data.pop(index)
        print(f"NPC Removido: {removed['name']}")
        refresh_npc_list()
        if editor_state["selected_npc_index"] == index:
            editor_state["selected_npc_index"] = None
        redraw_map("map_drawlist")

def update_npc_sprite_combo():
    # Atualiza a lista de sprites disponíveis no combo box
    if dpg.does_item_exist("input_npc_sprite"):
        items = [f"{id}: {info['name']}" for id, info in TILES.items() if id > 0]
        dpg.configure_item("input_npc_sprite", items=items)

# --- FUNÇÕES DE DESENHO ---

def redraw_map(drawlist_tag):
    dpg.delete_item(drawlist_tag, children_only=True)

    draw_width = GRID_WIDTH_CELLS * TILE_SIZE_PX
    draw_height = GRID_HEIGHT_CELLS * TILE_SIZE_PX

    cam = editor_state["camera"]

    # Define quais camadas desenhar baseado no modo de visualização
    view_mode = editor_state.get("view_mode", "Ver Todas")
    current_layer = editor_state["current_layer"]
    layers_to_draw = []

    if view_mode == "Ver Todas":
        layers_to_draw = range(NUM_LAYERS)
    elif view_mode == "Apenas Atual":
        layers_to_draw = [current_layer]
    elif view_mode == "Atual + Anterior":
        # Mostra a camada atual e a imediatamente anterior (se existir)
        prev_layer = current_layer - 1 if current_layer > 0 else 0
        layers_to_draw = sorted(list(set([prev_layer, current_layer])))

    for layer in layers_to_draw:
        # Define a cor de tingimento (transparência)
        tint_color = (255, 255, 255, 255)
        
        if view_mode == "Atual + Anterior":
            # Aplica transparência em ambas para ver sobreposição
            if current_layer == 0:
                # Se estamos na primeira camada, não faz sentido ter transparência pois não há nada embaixo
                tint_color = (255, 255, 255, 255)
            elif layer == current_layer:
                tint_color = (255, 255, 255, 100) # Atual bem transparente (~40%) para ver o fundo
            else:
                tint_color = (255, 255, 255, 255) # Anterior sólida para servir de referência

        for row in range(GRID_HEIGHT_CELLS):
            for col in range(GRID_WIDTH_CELLS):
                tile_id = map_data[layer][row][col]
                
                # Pula o ID 0 (Vazio) ou se o tile não existir
                if tile_id == 0 or tile_id not in TILES:
                    continue

                texture_tag = TILES[tile_id]["texture_tag"]
                
                # Calcula a posição na tela aplicando Zoom e Câmera
                # Fórmula: (Posição * Zoom) + Camera
                x1 = (col * TILE_SIZE_PX * cam["zoom"]) + cam["x"]
                y1 = (row * TILE_SIZE_PX * cam["zoom"]) + cam["y"]
                x2 = ((col + 1) * TILE_SIZE_PX * cam["zoom"]) + cam["x"]
                y2 = ((row + 1) * TILE_SIZE_PX * cam["zoom"]) + cam["y"]
                
                # Desenha a imagem (sprite) no grid
                dpg.draw_image(texture_tag, (x1, y1), (x2, y2), uv_min=(0, 0), uv_max=(1, 1), color=tint_color, parent=drawlist_tag)

    # Redesenha as linhas do grid por cima
    # Ajustamos para desenhar apenas as linhas visíveis ou transformadas
    for i in range(0, draw_width + 1, TILE_SIZE_PX):
        x = (i * cam["zoom"]) + cam["x"]
        y_start = cam["y"]
        y_end = (draw_height * cam["zoom"]) + cam["y"]
        dpg.draw_line((x, y_start), (x, y_end), color=(255, 255, 255, 30), thickness=1, parent=drawlist_tag)
        
    for i in range(0, draw_height + 1, TILE_SIZE_PX):
        y = (i * cam["zoom"]) + cam["y"]
        x_start = cam["x"]
        x_end = (draw_width * cam["zoom"]) + cam["x"]
        dpg.draw_line((x_start, y), (x_end, y), color=(255, 255, 255, 30), thickness=1, parent=drawlist_tag)

    # Desenha os NPCs (Por enquanto, círculos vermelhos para teste)
    for npc in npc_data:
        # Posição no mundo (em pixels)
        world_x = npc["x"]
        world_y = npc["y"]
        sprite_id = npc.get("sprite_id", 1)
        
        # Converte para tela
        screen_x = (world_x * cam["zoom"]) + cam["x"]
        screen_y = (world_y * cam["zoom"]) + cam["y"]
        
        # Se tivermos o sprite, desenhamos ele
        if sprite_id in TILES:
            texture_tag = TILES[sprite_id]["texture_tag"]
            size = TILE_SIZE_PX * cam["zoom"]
            
            # Se este NPC estiver selecionado, desenha um contorno ou destaque
            if editor_state.get("selected_npc_index") == npc_data.index(npc):
                 dpg.draw_circle((screen_x + size/2, screen_y + size/2), size/1.5, color=(0, 255, 0, 255), thickness=2, parent=drawlist_tag)

            dpg.draw_image(texture_tag, (screen_x, screen_y), (screen_x + size, screen_y + size), parent=drawlist_tag)
        else:
            # Fallback se não achar o sprite
            radius = (TILE_SIZE_PX / 2) * cam["zoom"]
            dpg.draw_circle((screen_x + radius, screen_y + radius), radius, color=(255, 0, 0, 255), fill=(255, 0, 0, 100), parent=drawlist_tag)
            
        dpg.draw_text((screen_x, screen_y - 20), npc.get("name", "NPC"), size=16 * cam["zoom"], parent=drawlist_tag)


# --- JANELAS DO EDITOR ---

def refresh_palette():
    """Limpa e recria a lista de tiles na paleta baseado na camada atual"""
    # Limpa o container de tiles
    dpg.delete_item("palette_content", children_only=True)
    
    current_layer = editor_state["current_layer"]
    
    # Recria a lista filtrada
    for tile_id, tile_info in TILES.items():
        if tile_id == 0: continue
        
        # FILTRAGEM INTELIGENTE
        target = tile_info.get("layer_target", 0)
        if current_layer < 3:
            # Camadas visuais: mostram apenas sprites normais (target 0)
            if target != 0: continue 
        else:
            # Camadas de dados: mostram apenas marcadores daquela camada
            if target != current_layer: continue

        # Adiciona ao grupo "palette_content"
        with dpg.group(horizontal=True, parent="palette_content"):
            dpg.add_image_button(
                tile_info['texture_tag'],
                callback=select_tile,
                user_data=tile_id,
                width=TILE_SIZE_PX,
                height=TILE_SIZE_PX,
            )
            with dpg.group():
                dpg.add_spacer(height=10)
                dpg.add_text(tile_info['name'])

    # Se a lista estiver vazia
    if current_layer >= 3 and not any(t.get("layer_target") == current_layer for t in TILES.values()):
            dpg.add_text("(Nenhum marcador disponivel)", parent="palette_content")

def show_tile_palette():
    with dpg.window(tag="janela_paleta", label="Paleta de Tiles", width=260, pos=(10, 50), no_close=True):
        dpg.add_text("Clique para selecionar:")
        dpg.add_separator()
        
        dpg.add_text("Camada Ativa:")
        dpg.add_radio_button(
            items=LAYER_NAMES,
            default_value=LAYER_NAMES[0],
            callback=change_layer,
            horizontal=False
        )
        dpg.add_separator()

        dpg.add_text("Modo de Visao:")
        dpg.add_radio_button(
            items=["Ver Todas", "Apenas Atual", "Atual + Anterior"],
            default_value="Ver Todas",
            callback=change_view_mode,
            horizontal=False
        )
        dpg.add_separator()
        
        # Botão de emergência para achar o mapa
        dpg.add_button(label="Resetar Camera (Centralizar)", callback=reset_camera_callback, width=-1)
        dpg.add_separator()

        # Botão especial para apagar
        # Deixamos ele fixo aqui fora do grupo dinâmico
        dpg.add_button(label="Apagar (Vazio)", callback=select_tile, user_data=0, width=-1)
        dpg.add_separator()

        # Criamos um grupo vazio que será preenchido pela função refresh_palette
        dpg.add_group(tag="palette_content")

        dpg.add_separator()
        initial_selected_id = editor_state['selected_tile_id']
        initial_name = TILES.get(initial_selected_id, {}).get('name', 'Nenhum')
        dpg.add_text(f"Selecionado: {initial_name}", tag="selected_tile_text")
    
    # Chama a função para preencher a paleta pela primeira vez
    refresh_palette()

def show_npc_editor(sender, app_data):
    if dpg.does_item_exist("janela_npcs"):
        dpg.show_item("janela_npcs")
        dpg.focus_item("janela_npcs")
        return

    with dpg.window(tag="janela_npcs", label="Gerenciador de NPCs", width=300, height=400, pos=(50, 50)):
        dpg.add_text("Criar Novo NPC")
        dpg.add_input_text(tag="input_npc_name", label="Nome", default_value="Goblin")
        
        # Combo box para escolher o sprite
        dpg.add_combo(tag="input_npc_sprite", items=[], label="Sprite", width=150)
        
        dpg.add_separator()
        dpg.add_input_int(tag="input_npc_hp", label="Vida (HP)", default_value=10, width=100)
        dpg.add_input_int(tag="input_npc_attack", label="Ataque", default_value=2, width=100)
        
        with dpg.group(horizontal=True):
            dpg.add_button(label="Adicionar", callback=add_npc_callback)
            dpg.add_button(label="Salvar Edicao", callback=save_npc_callback)
            
        dpg.add_separator()
        dpg.add_text("Lista de NPCs:")
        dpg.add_group(tag="list_npcs")
        
        update_npc_sprite_combo()
        refresh_npc_list()

def show_map_editor(sender, app_data):
    if dpg.does_item_exist("janela_mapa"):
        dpg.show_item("janela_mapa")
        dpg.focus_item("janela_mapa")
        return

    draw_width = GRID_WIDTH_CELLS * TILE_SIZE_PX
    draw_height = GRID_HEIGHT_CELLS * TILE_SIZE_PX
    
    with dpg.window(tag="janela_mapa", label="Editor de Mapas", width=draw_width + 40, height=draw_height + 80, pos=(240, 50), no_close=True):
        dpg.add_text("Area de Desenho do Mapa")
        with dpg.drawlist(width=draw_width, height=draw_height, tag="map_drawlist"):
            redraw_map("map_drawlist")

def run_editor():
    dpg.create_context()
    
    # Container invisível para registrar as texturas
    with dpg.texture_registry(show=False, tag="texture_container"):
        pass

    # Carrega e registra todos os sprites antes de qualquer outra coisa
    load_and_register_sprites()
    
    dpg.create_viewport(title='Pandorha Forge - Editor de RPG', width=1280, height=720)
    dpg.setup_dearpygui()
    dpg.configure_app(docking=True, docking_space=True)

    with dpg.file_dialog(
        directory_selector=False, show=False, callback=_save_map_callback, tag="file_dialog_save_map",
        file_count=1, default_filename="novo_mapa.json", width=700 ,height=400):
        dpg.add_file_extension(".json", color=(0, 255, 255, 255))

    with dpg.file_dialog(
        directory_selector=False, show=False, callback=_load_map_callback, tag="file_dialog_load_map",
        file_count=1, width=700 ,height=400):
        dpg.add_file_extension(".json", color=(0, 255, 255, 255))

    with dpg.handler_registry():
        # Alterado de 'click' para 'down' para permitir pintar/apagar arrastando
        dpg.add_mouse_down_handler(button=dpg.mvMouseButton_Left, callback=paint_on_map_callback)
        dpg.add_mouse_release_handler(button=dpg.mvMouseButton_Left, callback=map_mouse_release_left_callback)
        # Especificamos button=dpg.mvMouseButton_Right para evitar conflito com o clique esquerdo
        dpg.add_mouse_drag_handler(button=dpg.mvMouseButton_Right, callback=map_drag_callback)
        dpg.add_mouse_release_handler(button=dpg.mvMouseButton_Right, callback=map_mouse_release_callback)
        dpg.add_mouse_wheel_handler(callback=map_zoom_callback)

    with dpg.viewport_menu_bar():
        with dpg.menu(label="Arquivo"):
            dpg.add_menu_item(label="Salvar Mapa...", callback=lambda: dpg.show_item("file_dialog_save_map"))
            dpg.add_menu_item(label="Carregar Mapa...", callback=lambda: dpg.show_item("file_dialog_load_map"))
            dpg.add_separator()
            dpg.add_menu_item(label="Sair", callback=dpg.stop_dearpygui)
        with dpg.menu(label="Modulos"):
            dpg.add_menu_item(label="Editor de Mapas", callback=show_map_editor)
            dpg.add_menu_item(label="Editor de NPCs", callback=show_npc_editor)
    
    # Mostra as janelas principais
    show_tile_palette()
    # Abre o editor de mapas por padrão
    show_map_editor(None, None)

    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()

if __name__ == "__main__":
    run_editor()
