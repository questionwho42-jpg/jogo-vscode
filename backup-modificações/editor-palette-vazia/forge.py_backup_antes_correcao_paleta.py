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

# O dicionário de TILES agora será preenchido dinamicamente
TILES = {}
# O registro de texturas também será preenchido dinamicamente
TEXTURE_REGISTRY = {}
# Armazenamento para os dados brutos da textura para evitar que o garbage collector do Python os limpe
TEXTURE_DATA_STORAGE = []

# Estado atual do editor
editor_state = {
    "selected_tile_id": 0  # Usaremos o ID 0 como padrão
}

# Estrutura de dados que guarda o mapa
map_data = [[0 for _ in range(GRID_WIDTH_CELLS)] for _ in range(GRID_HEIGHT_CELLS)]


def load_and_register_sprites():
    """
    Escaneia a pasta 'assets/sprites', carrega as imagens .webp,
    as registra como texturas no DPG e preenche o dicionário TILES.
    """
    global TILES, TEXTURE_REGISTRY
    TILES.clear()
    TEXTURE_REGISTRY.clear()
    TEXTURE_DATA_STORAGE.clear()

    sprite_path = Path("assets/sprites")
    if not sprite_path.is_dir():
        print(f"Aviso: Diretório de sprites '{sprite_path}' não encontrado.")
        return

    # Usaremos um ID numérico incremental para cada tile
    tile_id_counter = 0

    # Adiciona um tile "Vazio" (ID 0) por padrão
    TILES[0] = {"name": "Vazio", "texture_tag": None}
    tile_id_counter += 1

    # Busca por todos os arquivos .webp
    sprite_files = sorted(list(sprite_path.glob("*.webp")))

    for webp_path in sprite_files:
        try:
            with Image.open(webp_path) as img:
                # Converte a imagem para RGBA, que é o que o DPG espera
                img_rgba = img.convert("RGBA")
                width, height = img.size
                # Converte os dados da imagem para um formato que o DPG entende
                texture_data = img_rgba.tobytes()
                TEXTURE_DATA_STORAGE.append(texture_data)

            # Registra a textura no DearPyGui usando o método moderno para dados brutos
            texture_tag = dpg.add_raw_texture(
                width,
                height,
                texture_data,
                format=dpg.mvFormat_RGBA, # Formato para bytes RGBA (0-255)
                parent="texture_container"
            )
            
            # Guarda a tag da textura para referência futura
            TEXTURE_REGISTRY[tile_id_counter] = texture_tag

            # Adiciona a informação do tile ao nosso dicionário
            tile_name = webp_path.stem.replace("_", " ").title() # Ex: "grass_tile" -> "Grass Tile"
            TILES[tile_id_counter] = {"name": tile_name, "texture_tag": texture_tag}
            
            print(f"Carregado Sprite: '{tile_name}' (ID: {tile_id_counter})")
            tile_id_counter += 1

        except Exception as e:
            print(f"Erro ao carregar o sprite '{webp_path.name}': {e}")
            
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
            if (len(loaded_data) == GRID_HEIGHT_CELLS and
                all(len(row) == GRID_WIDTH_CELLS for row in loaded_data)):
                map_data = loaded_data
                print("Mapa carregado com sucesso!")
                redraw_map("map_drawlist")
            else:
                print("Erro: O arquivo de mapa parece ter dimensões inválidas.")

    except Exception as e:
        print(f"Ocorreu um erro ao carregar o mapa: {e}")

def select_tile(sender, app_data, user_data):
    tile_id = user_data
    editor_state["selected_tile_id"] = tile_id
    dpg.set_value("selected_tile_text", f"Selecionado: {TILES[tile_id]['name']}")

def paint_on_map_callback(sender, app_data):
    if app_data != dpg.mvMouseButton_Left:
        return

    if dpg.is_item_hovered("map_drawlist"):
        mouse_pos = dpg.get_drawing_mouse_pos()
        col = int(mouse_pos[0] / TILE_SIZE_PX)
        row = int(mouse_pos[1] / TILE_SIZE_PX)

        if 0 <= row < GRID_HEIGHT_CELLS and 0 <= col < GRID_WIDTH_CELLS:
            # Verifica se a célula clicada já tem o tile selecionado para evitar redesenhos
            if map_data[row][col] != editor_state["selected_tile_id"]:
                map_data[row][col] = editor_state["selected_tile_id"]
                redraw_map("map_drawlist")

# --- FUNÇÕES DE DESENHO ---

def redraw_map(drawlist_tag):
    dpg.delete_item(drawlist_tag, children_only=True)

    draw_width = GRID_WIDTH_CELLS * TILE_SIZE_PX
    draw_height = GRID_HEIGHT_CELLS * TILE_SIZE_PX

    for row in range(GRID_HEIGHT_CELLS):
        for col in range(GRID_WIDTH_CELLS):
            tile_id = map_data[row][col]
            
            # Pula o ID 0 (Vazio) ou se o tile não existir
            if tile_id == 0 or tile_id not in TILES:
                continue

            texture_tag = TILES[tile_id]["texture_tag"]
            p1 = (col * TILE_SIZE_PX, row * TILE_SIZE_PX)
            p2 = ((col + 1) * TILE_SIZE_PX, (row + 1) * TILE_SIZE_PX)
            
            # Desenha a imagem (sprite) no grid, especificando as coordenadas UV
            # uv_min=(0,0) e uv_max=(1,1) garante que a imagem inteira seja usada
            dpg.draw_image(texture_tag, p1, p2, uv_min=(0, 0), uv_max=(1, 1), parent=drawlist_tag)

    # Redesenha as linhas do grid por cima
    for i in range(0, draw_width + 1, TILE_SIZE_PX):
        dpg.draw_line((i, 0), (i, draw_height), color=(255, 255, 255, 30), thickness=1, parent=drawlist_tag)
    for i in range(0, draw_height + 1, TILE_SIZE_PX):
        dpg.draw_line((0, i), (draw_width, i), color=(255, 255, 255, 30), thickness=1, parent=drawlist_tag)


# --- JANELAS DO EDITOR ---

def show_tile_palette():
    with dpg.window(tag="janela_paleta", label="Paleta de Tiles", width=220, pos=(10, 50), no_close=True):
        dpg.add_text("Clique para selecionar:")
        dpg.add_separator()
        
        # Cria os botões da paleta dinamicamente
        for tile_id, tile_info in TILES.items():
            # Pula o tile "Vazio"
            if tile_id == 0:
                dpg.add_button(label="Apagar (Vazio)", callback=select_tile, user_data=0, width=-1)
                continue

            # Adiciona um botão com a imagem do sprite
            dpg.add_image_button(tile_info['texture_tag'], callback=select_tile, user_data=tile_id, width=TILE_SIZE_PX, height=TILE_SIZE_PX)
            dpg.add_same_line()
            dpg.add_text(tile_info['name'])


        dpg.add_separator()
        # Garante que temos um tile selecionado antes de tentar pegar o nome
        initial_selected_id = editor_state['selected_tile_id']
        initial_name = TILES.get(initial_selected_id, {}).get('name', 'Nenhum')
        dpg.add_text(f"Selecionado: {initial_name}", tag="selected_tile_text")


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