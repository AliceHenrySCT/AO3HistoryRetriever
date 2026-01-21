from PIL import Image, ImageDraw, ImageFont
import os

def create_gradient(width, height, color1, color2):
    """Create a vertical gradient from color1 to color2"""
    base = Image.new('RGB', (width, height), color1)
    top = Image.new('RGB', (width, height), color2)
    mask = Image.new('L', (width, height))
    mask_data = []
    for y in range(height):
        mask_data.extend([int(255 * (y / height))] * width)
    mask.putdata(mask_data)
    base.paste(top, (0, 0), mask)
    return base

def get_font(size):
    """Try to get a nice font, fall back to default if unavailable"""
    font_paths = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/System/Library/Fonts/Helvetica.ttc',
        '/Windows/Fonts/arial.ttf'
    ]

    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except:
                pass

    return ImageFont.load_default()

def draw_text_with_outline(draw, position, text, font, fill_color, outline_color, outline_width=2):
    """Draw text with an outline for better readability"""
    x, y = position
    # Draw outline
    for adj_x in range(-outline_width, outline_width + 1):
        for adj_y in range(-outline_width, outline_width + 1):
            draw.text((x + adj_x, y + adj_y), text, font=font, fill=outline_color)
    # Draw text
    draw.text(position, text, font=font, fill=fill_color)

def create_top_ships_image(ships, output_path):
    """Create an image showing top 5 ships"""
    width, height = 800, 600

    # Create gradient background (romantic pink to purple)
    img = create_gradient(width, height, (255, 182, 193), (221, 160, 221))
    draw = ImageDraw.Draw(img)

    # Title
    title_font = get_font(60)
    draw_text_with_outline(draw, (40, 40), "Top Ships", title_font, (255, 255, 255), (100, 50, 100), 3)

    # Draw ships
    y_offset = 150
    item_font = get_font(36)
    count_font = get_font(32)

    for i, ship in enumerate(ships[:5]):
        ship_name = ship['ship']
        count = ship['count']

        # Rank circle
        draw.ellipse([40, y_offset, 90, y_offset + 50], fill=(255, 255, 255, 200), outline=(100, 50, 100), width=3)
        rank_font = get_font(32)
        rank_text = f"#{i+1}"
        bbox = draw.textbbox((0, 0), rank_text, font=rank_font)
        rank_width = bbox[2] - bbox[0]
        draw.text((65 - rank_width // 2, y_offset + 8), rank_text, font=rank_font, fill=(100, 50, 100))

        # Ship name
        draw.text((110, y_offset + 5), ship_name[:50], font=item_font, fill=(255, 255, 255))

        # Count
        count_text = f"{count} fics"
        bbox = draw.textbbox((0, 0), count_text, font=count_font)
        count_width = bbox[2] - bbox[0]
        draw.text((width - count_width - 40, y_offset + 8), count_text, font=count_font, fill=(255, 255, 255))

        y_offset += 80

    img.save(output_path, 'PNG')
    return output_path

def create_top_tags_image(tags, output_path):
    """Create an image showing top 5 tags"""
    width, height = 800, 600

    # Create gradient background (blue to teal)
    img = create_gradient(width, height, (135, 206, 250), (64, 224, 208))
    draw = ImageDraw.Draw(img)

    # Title
    title_font = get_font(60)
    draw_text_with_outline(draw, (40, 40), "Top Tags", title_font, (255, 255, 255), (20, 80, 100), 3)

    # Draw tags
    y_offset = 150
    item_font = get_font(36)
    count_font = get_font(32)

    for i, tag in enumerate(tags[:5]):
        tag_name = tag['tag']
        count = tag['count']

        # Rank circle
        draw.ellipse([40, y_offset, 90, y_offset + 50], fill=(255, 255, 255, 200), outline=(20, 80, 100), width=3)
        rank_font = get_font(32)
        rank_text = f"#{i+1}"
        bbox = draw.textbbox((0, 0), rank_text, font=rank_font)
        rank_width = bbox[2] - bbox[0]
        draw.text((65 - rank_width // 2, y_offset + 8), rank_text, font=rank_font, fill=(20, 80, 100))

        # Tag name
        draw.text((110, y_offset + 5), tag_name[:50], font=item_font, fill=(255, 255, 255))

        # Count
        count_text = f"{count} fics"
        bbox = draw.textbbox((0, 0), count_text, font=count_font)
        count_width = bbox[2] - bbox[0]
        draw.text((width - count_width - 40, y_offset + 8), count_text, font=count_font, fill=(255, 255, 255))

        y_offset += 80

    img.save(output_path, 'PNG')
    return output_path

def create_top_fandoms_image(fandoms, output_path):
    """Create an image showing top 5 fandoms"""
    width, height = 800, 600

    # Create gradient background (orange to coral)
    img = create_gradient(width, height, (255, 165, 0), (255, 127, 80))
    draw = ImageDraw.Draw(img)

    # Title
    title_font = get_font(60)
    draw_text_with_outline(draw, (40, 40), "Top Fandoms", title_font, (255, 255, 255), (150, 50, 30), 3)

    # Draw fandoms
    y_offset = 150
    item_font = get_font(36)
    count_font = get_font(32)

    for i, fandom in enumerate(fandoms[:5]):
        fandom_name = fandom['fandom']
        count = fandom['count']

        # Rank circle
        draw.ellipse([40, y_offset, 90, y_offset + 50], fill=(255, 255, 255, 200), outline=(150, 50, 30), width=3)
        rank_font = get_font(32)
        rank_text = f"#{i+1}"
        bbox = draw.textbbox((0, 0), rank_text, font=rank_font)
        rank_width = bbox[2] - bbox[0]
        draw.text((65 - rank_width // 2, y_offset + 8), rank_text, font=rank_font, fill=(150, 50, 30))

        # Fandom name
        draw.text((110, y_offset + 5), fandom_name[:50], font=item_font, fill=(255, 255, 255))

        # Count
        count_text = f"{count} fics"
        bbox = draw.textbbox((0, 0), count_text, font=count_font)
        count_width = bbox[2] - bbox[0]
        draw.text((width - count_width - 40, y_offset + 8), count_text, font=count_font, fill=(255, 255, 255))

        y_offset += 80

    img.save(output_path, 'PNG')
    return output_path

def create_overall_stats_image(stats, output_path):
    """Create an image showing overall reading stats"""
    width, height = 800, 600

    # Create gradient background (emerald to teal)
    img = create_gradient(width, height, (16, 185, 129), (20, 184, 166))
    draw = ImageDraw.Draw(img)

    # Title
    title_font = get_font(60)
    draw_text_with_outline(draw, (40, 40), "Reading Stats", title_font, (255, 255, 255), (10, 100, 90), 3)

    # Stats
    y_offset = 150
    label_font = get_font(32)
    value_font = get_font(48)

    # Total fics
    draw.text((80, y_offset), "Total Fics Read", font=label_font, fill=(230, 255, 250))
    draw.text((80, y_offset + 45), f"{stats['totalFics']:,}", font=value_font, fill=(255, 255, 255))

    y_offset += 130

    # Total words
    draw.text((80, y_offset), "Total Words Read", font=label_font, fill=(230, 255, 250))
    draw.text((80, y_offset + 45), f"{stats['totalWords']:,}", font=value_font, fill=(255, 255, 255))

    y_offset += 130

    # Longest fic
    draw.text((80, y_offset), "Longest Fic", font=label_font, fill=(230, 255, 250))
    longest_text = f"{stats['longestFic']['wordCount']:,} words"
    draw.text((80, y_offset + 45), longest_text, font=value_font, fill=(255, 255, 255))

    # Longest fic title (smaller)
    if stats['longestFic']['title']:
        title_font_small = get_font(24)
        title_text = stats['longestFic']['title'][:60]
        if len(stats['longestFic']['title']) > 60:
            title_text += "..."
        draw.text((80, y_offset + 100), title_text, font=title_font_small, fill=(240, 255, 252))

    img.save(output_path, 'PNG')
    return output_path

def generate_all_stat_images(statistics):
    """Generate all stat images and return their paths"""
    output_dir = '/tmp/ao3_stats'
    os.makedirs(output_dir, exist_ok=True)

    image_paths = {}

    # Generate each image
    if statistics['topShips']:
        image_paths['ships'] = create_top_ships_image(
            statistics['topShips'],
            os.path.join(output_dir, 'top_ships.png')
        )

    if statistics['topTags']:
        image_paths['tags'] = create_top_tags_image(
            statistics['topTags'],
            os.path.join(output_dir, 'top_tags.png')
        )

    if statistics['topFandoms']:
        image_paths['fandoms'] = create_top_fandoms_image(
            statistics['topFandoms'],
            os.path.join(output_dir, 'top_fandoms.png')
        )

    image_paths['overall'] = create_overall_stats_image(
        statistics,
        os.path.join(output_dir, 'overall_stats.png')
    )

    return image_paths
