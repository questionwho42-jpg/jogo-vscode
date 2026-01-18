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
NUM_LAYERS = 6 
# 0=Chão, 1=Objetos, 2=Topo (Visuais)
# 3=Som, 4=Luz, 5=Cheiro (Dados)

LAYER_NAMES = [
    "1. Chao (Visual)", "2. Objetos (Visual)", "3. Topo (Visual)",
    "4. Sons (Dados)", "5. Luzes (Dados)", "6. Cheiros (Dados)"
]

# O dicionário de TILES agora será preenchido dinamicamente
TILES = {}
# O registro de texturas também será preenchido dinamicamente
TEXTURE_REGISTRY = {}

# Estado atual do editor
editor_state = {
    "selected_tile_id": 0,  # Usaremos o ID 0 como padrão
    "current_layer": 0,     # Começa editando a camada 0 (Chão)
    "view_mode": "Ver Todas" # Modos: "Ver Todas", "Apenas Atual", "Atual + Anterior"
}

# Estrutura de dados que guarda o mapa (Agora com camadas!)
# É uma lista de 3 grids. map_data[0] é o chão, map_data[1] objetos, etc.
map_data = [
    [[0 for _ in range(GRID_WIDTH_CELLS)] for _ in range(GRID_HEIGHT_CELLS)] for _ in range(NUM_LAYERS)
]

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
    file_path_name = app_data['file_path_name']
    print(f"Salvando mapa em: {file_path_name}")
    try:
        with open(file_path_name, 'w') as f:
            json.dump(map_data, f, indent=4)
        print("Mapa salvo com sucesso!")
    except Exception as e:
        print(f"Ocorreu um erro ao salvar o mapa: {e}")

def _load_map_callback(sender, app_data):
    global map_data
    file_path_name = app_data['file_path_name']
    print(f"Carregando mapa de: {file_path_name}")
    try:
        with open(file_path_name, 'r') as f:
            loaded_data = json.load(f)
            
            # Verifica se é um mapa novo (com camadas) ou antigo (sem camadas)
            # Se o primeiro item for uma lista de listas, é o formato novo (3D)
            if isinstance(loaded_data[0][0], list):
                map_data = loaded_data
                print("Mapa (com camadas) carregado com sucesso!")
                
                # Se o mapa carregado tiver menos camadas que o editor atual (ex: mapa antigo de 3 camadas), expande
                while len(map_data) < NUM_LAYERS:
                    map_data.append([[0] * GRID_WIDTH_CELLS for _ in range(GRID_HEIGHT_CELLS)])
                
                redraw_map("map_drawlist")
            # Se for formato antigo (2D), carregamos na camada 0 e limpamos as outras
            elif len(loaded_data) == GRID_HEIGHT_CELLS:
                map_data = [loaded_data] + [[[0] * GRID_WIDTH_CELLS for _ in range(GRID_HEIGHT_CELLS)] for _ in range(NUM_LAYERS - 1)]
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

def paint_on_map_callback(sender, app_data):
    if app_data != dpg.mvMouseButton_Left:
        return
    
    # TODO: Adicionar verificação se o tile selecionado é compatível com a camada atual

    if dpg.is_item_hovered("map_drawlist"):
        mouse_pos = dpg.get_drawing_mouse_pos()
        col = int(mouse_pos[0] / TILE_SIZE_PX)
        row = int(mouse_pos[1] / TILE_SIZE_PX)

        if 0 <= row < GRID_HEIGHT_CELLS and 0 <= col < GRID_WIDTH_CELLS:
            # Verifica se a célula clicada já tem o tile selecionado para evitar redesenhos
            layer = editor_state["current_layer"]
            if map_data[layer][row][col] != editor_state["selected_tile_id"]:
                map_data[layer][row][col] = editor_state["selected_tile_id"]
                redraw_map("map_drawlist")

# --- FUNÇÕES DE DESENHO ---

def redraw_map(drawlist_tag):
    dpg.delete_item(drawlist_tag, children_only=True)

    draw_width = GRID_WIDTH_CELLS * TILE_SIZE_PX
    draw_height = GRID_HEIGHT_CELLS * TILE_SIZE_PX

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
                p1 = (col * TILE_SIZE_PX, row * TILE_SIZE_PX)
                p2 = ((col + 1) * TILE_SIZE_PX, (row + 1) * TILE_SIZE_PX)
                
                # Desenha a imagem (sprite) no grid
                dpg.draw_image(texture_tag, p1, p2, uv_min=(0, 0), uv_max=(1, 1), color=tint_color, parent=drawlist_tag)

    # Redesenha as linhas do grid por cima
    for i in range(0, draw_width + 1, TILE_SIZE_PX):
        dpg.draw_line((i, 0), (i, draw_height), color=(255, 255, 255, 30), thickness=1, parent=drawlist_tag)
    for i in range(0, draw_height + 1, TILE_SIZE_PX):
        dpg.draw_line((0, i), (draw_width, i), color=(255, 255, 255, 30), thickness=1, parent=drawlist_tag)


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
                frame_padding=2
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
        dpg.add_mouse_click_handler(callback=paint_on_map_callback)

    with dpg.viewport_menu_bar():
        with dpg.menu(label="Arquivo"):
            dpg.add_menu_item(label="Salvar Mapa...", callback=lambda: dpg.show_item("file_dialog_save_map"))
            dpg.add_menu_item(label="Carregar Mapa...", callback=lambda: dpg.show_item("file_dialog_load_map"))
            dpg.add_separator()
            dpg.add_menu_item(label="Sair", callback=dpg.stop_dearpygui)
        with dpg.menu(label="Modulos"):
            dpg.add_menu_item(label="Editor de Mapas", callback=show_map_editor)
            dpg.add_menu_item(label="Editor de NPCs")
    
    # Mostra as janelas principais
    show_tile_palette()
    # Abre o editor de mapas por padrão
    show_map_editor(None, None)

    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()

if __name__ == "__main__":
    run_editor()
