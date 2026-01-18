from pathlib import Path
from PIL import Image
import sys

# Garante que o terminal possa exibir caracteres especiais corretamente
sys.stdout.reconfigure(encoding='utf-8')

def convert_png_to_webp():
    """
    Encontra todos os arquivos .png na pasta 'assets' e seus subdiretórios
    e os converte para o formato .webp.
    """
    # O caminho para a pasta de assets
    assets_path = Path("assets")
    if not assets_path.is_dir():
        print(f"❌ Erro: O diretório '{assets_path}' não foi encontrado.")
        return

    print("🔎 Procurando por arquivos .png para converter em .webp...")

    # .rglob('*.png') busca recursivamente por todos os arquivos que terminam com .png
    png_files = list(assets_path.rglob("*.png"))

    if not png_files:
        print("✅ Nenhum arquivo .png encontrado para conversão.")
        return

    converted_count = 0
    for png_path in png_files:
        # Cria o caminho para o novo arquivo .webp, mantendo o mesmo nome
        webp_path = png_path.with_suffix(".webp")
        
        # Evita reconverter um arquivo que já existe
        if webp_path.exists():
            print(f"⏭️  Ignorando '{png_path.name}', pois a versão .webp já existe.")
            continue

        try:
            # Abre a imagem PNG
            with Image.open(png_path) as im:
                # Salva a imagem no formato WebP com qualidade alta e sem perdas
                im.save(webp_path, format="webp", quality=95, lossless=True)
            print(f"✅ Convertido: '{png_path.name}' -> '{webp_path.name}'")
            converted_count += 1
        except Exception as e:
            print(f"❌ Erro ao converter '{png_path.name}': {e}")

    print(f"\nConversão concluída! {converted_count} novos arquivos .webp foram criados.")

if __name__ == "__main__":
    convert_png_to_webp()
