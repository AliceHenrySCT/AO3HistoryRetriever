from PIL import Image, ImageDraw, ImageFont
import os

def create_gradient(width, height, color1, color2):
    """Create a subtle vertical gradient from color1 to color2"""
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

def draw_text_centered(draw, y, text, font, fill_color, width):
    """Draw centered text"""
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    x = (width - text_width) // 2
    draw.text((x, y), text, font=font, fill=fill_color)

def wrap_text(text, font, max_width, draw):
    """Wrap text to fit within max_width"""
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]

    if current_line:
        lines.append(' '.join(current_line))

    return lines

def create_top_ships_image(ships, output_path):
    """Create an image showing top 5 ships"""
    width, height = 1080, 1920

    # Create subtle gradient background (AO3 maroon shades)
    img = create_gradient(width, height, (115, 0, 10), (74, 0, 6))
    draw = ImageDraw.Draw(img)

    # Header section with title
    header_height = 280
    draw.rectangle([0, 0, width, header_height], fill=(153, 0, 17))

    title_font = get_font(90)
    draw_text_centered(draw, 90, "Top Ships", title_font, (255, 255, 255), width)

    # Subtitle
    subtitle_font = get_font(42)
    draw_text_centered(draw, 190, "Your Most Read Relationships", subtitle_font, (255, 220, 220), width)

    # Draw ships
    y_offset = 400
    item_font = get_font(52)
    count_font = get_font(44)

    for i, ship in enumerate(ships[:5]):
        ship_name = ship['ship']
        count = ship['count']

        # Card background
        card_top = y_offset - 30
        card_bottom = y_offset + 160
        draw.rectangle([60, card_top, width - 60, card_bottom],
                      fill=(255, 245, 245), outline=(153, 0, 17), width=4)

        # Rank badge
        badge_size = 90
        badge_x = 100
        badge_y = y_offset + 10
        draw.ellipse([badge_x, badge_y, badge_x + badge_size, badge_y + badge_size],
                    fill=(153, 0, 17))

        rank_font = get_font(48)
        rank_text = f"{i+1}"
        bbox = draw.textbbox((0, 0), rank_text, font=rank_font)
        rank_width = bbox[2] - bbox[0]
        draw.text((badge_x + (badge_size - rank_width) // 2, badge_y + 18),
                 rank_text, font=rank_font, fill=(255, 255, 255))

        # Count (calculate position first)
        count_text = f"{count} fics"
        bbox = draw.textbbox((0, 0), count_text, font=count_font)
        count_width = bbox[2] - bbox[0]
        count_x = width - count_width - 100

        # Ship name (wrapped with proper width to avoid count)
        max_text_width = count_x - 250
        ship_lines = wrap_text(ship_name, item_font, max_text_width, draw)
        ship_y = y_offset + 20 if len(ship_lines) == 1 else y_offset

        for line in ship_lines[:2]:
            draw.text((230, ship_y), line, font=item_font, fill=(50, 0, 5))
            ship_y += 60

        # Draw count
        draw.text((count_x, y_offset + 55),
                 count_text, font=count_font, fill=(120, 0, 10))

        y_offset += 250

    img.save(output_path, 'PNG')
    return output_path

def create_top_tags_image(tags, output_path):
    """Create an image showing top 5 tags"""
    width, height = 1080, 1920

    # Create subtle gradient background (dark maroon to AO3 maroon)
    img = create_gradient(width, height, (90, 0, 8), (115, 0, 10))
    draw = ImageDraw.Draw(img)

    # Header section with title
    header_height = 280
    draw.rectangle([0, 0, width, header_height], fill=(153, 0, 17))

    title_font = get_font(90)
    draw_text_centered(draw, 90, "Top Tags", title_font, (255, 255, 255), width)

    # Subtitle
    subtitle_font = get_font(42)
    draw_text_centered(draw, 190, "Your Favorite Themes", subtitle_font, (255, 220, 220), width)

    # Draw tags
    y_offset = 400
    item_font = get_font(52)
    count_font = get_font(44)

    for i, tag in enumerate(tags[:5]):
        tag_name = tag['tag']
        count = tag['count']

        # Card background
        card_top = y_offset - 30
        card_bottom = y_offset + 160
        draw.rectangle([60, card_top, width - 60, card_bottom],
                      fill=(255, 245, 245), outline=(153, 0, 17), width=4)

        # Rank badge
        badge_size = 90
        badge_x = 100
        badge_y = y_offset + 10
        draw.ellipse([badge_x, badge_y, badge_x + badge_size, badge_y + badge_size],
                    fill=(153, 0, 17))

        rank_font = get_font(48)
        rank_text = f"{i+1}"
        bbox = draw.textbbox((0, 0), rank_text, font=rank_font)
        rank_width = bbox[2] - bbox[0]
        draw.text((badge_x + (badge_size - rank_width) // 2, badge_y + 18),
                 rank_text, font=rank_font, fill=(255, 255, 255))

        # Count (calculate position first)
        count_text = f"{count} fics"
        bbox = draw.textbbox((0, 0), count_text, font=count_font)
        count_width = bbox[2] - bbox[0]
        count_x = width - count_width - 100

        # Tag name (wrapped with proper width to avoid count)
        max_text_width = count_x - 250
        tag_lines = wrap_text(tag_name, item_font, max_text_width, draw)
        tag_y = y_offset + 20 if len(tag_lines) == 1 else y_offset

        for line in tag_lines[:2]:
            draw.text((230, tag_y), line, font=item_font, fill=(50, 0, 5))
            tag_y += 60

        # Draw count
        draw.text((count_x, y_offset + 55),
                 count_text, font=count_font, fill=(120, 0, 10))

        y_offset += 250

    img.save(output_path, 'PNG')
    return output_path

def create_top_fandoms_image(fandoms, output_path):
    """Create an image showing top 5 fandoms"""
    width, height = 1080, 1920

    # Create subtle gradient background (burgundy to deep maroon)
    img = create_gradient(width, height, (128, 0, 12), (90, 0, 8))
    draw = ImageDraw.Draw(img)

    # Header section with title
    header_height = 280
    draw.rectangle([0, 0, width, header_height], fill=(153, 0, 17))

    title_font = get_font(90)
    draw_text_centered(draw, 90, "Top Fandoms", title_font, (255, 255, 255), width)

    # Subtitle
    subtitle_font = get_font(42)
    draw_text_centered(draw, 190, "Your Favorite Universes", subtitle_font, (255, 220, 220), width)

    # Draw fandoms
    y_offset = 400
    item_font = get_font(52)
    count_font = get_font(44)

    for i, fandom in enumerate(fandoms[:5]):
        fandom_name = fandom['fandom']
        count = fandom['count']

        # Card background
        card_top = y_offset - 30
        card_bottom = y_offset + 160
        draw.rectangle([60, card_top, width - 60, card_bottom],
                      fill=(255, 245, 245), outline=(153, 0, 17), width=4)

        # Rank badge
        badge_size = 90
        badge_x = 100
        badge_y = y_offset + 10
        draw.ellipse([badge_x, badge_y, badge_x + badge_size, badge_y + badge_size],
                    fill=(153, 0, 17))

        rank_font = get_font(48)
        rank_text = f"{i+1}"
        bbox = draw.textbbox((0, 0), rank_text, font=rank_font)
        rank_width = bbox[2] - bbox[0]
        draw.text((badge_x + (badge_size - rank_width) // 2, badge_y + 18),
                 rank_text, font=rank_font, fill=(255, 255, 255))

        # Count (calculate position first)
        count_text = f"{count} fics"
        bbox = draw.textbbox((0, 0), count_text, font=count_font)
        count_width = bbox[2] - bbox[0]
        count_x = width - count_width - 100

        # Fandom name (wrapped with proper width to avoid count)
        max_text_width = count_x - 250
        fandom_lines = wrap_text(fandom_name, item_font, max_text_width, draw)
        fandom_y = y_offset + 20 if len(fandom_lines) == 1 else y_offset

        for line in fandom_lines[:2]:
            draw.text((230, fandom_y), line, font=item_font, fill=(50, 0, 5))
            fandom_y += 60

        # Draw count
        draw.text((count_x, y_offset + 55),
                 count_text, font=count_font, fill=(120, 0, 10))

        y_offset += 250

    img.save(output_path, 'PNG')
    return output_path

def create_overall_stats_image(stats, output_path):
    """Create an image showing overall reading stats"""
    width, height = 1080, 1920

    # Create subtle gradient background (AO3 maroon to dark burgundy)
    img = create_gradient(width, height, (115, 0, 10), (128, 0, 12))
    draw = ImageDraw.Draw(img)

    # Header section with title
    header_height = 280
    draw.rectangle([0, 0, width, header_height], fill=(153, 0, 17))

    title_font = get_font(90)
    draw_text_centered(draw, 90, "Reading Stats", title_font, (255, 255, 255), width)

    # Subtitle
    subtitle_font = get_font(42)
    draw_text_centered(draw, 190, "Your AO3 Journey", subtitle_font, (255, 220, 220), width)

    # Stats section
    y_offset = 450
    label_font = get_font(48)
    value_font = get_font(90)

    # Total fics card
    draw.rectangle([80, y_offset - 30, width - 80, y_offset + 220],
                  fill=(255, 245, 245), outline=(153, 0, 17), width=4)
    draw_text_centered(draw, y_offset + 20, "Total Fics Read", label_font, (120, 0, 10), width)
    draw_text_centered(draw, y_offset + 100, f"{stats['totalFics']:,}", value_font, (50, 0, 5), width)

    y_offset += 350

    # Total words card
    draw.rectangle([80, y_offset - 30, width - 80, y_offset + 220],
                  fill=(255, 245, 245), outline=(153, 0, 17), width=4)
    draw_text_centered(draw, y_offset + 20, "Total Words Read", label_font, (120, 0, 10), width)
    draw_text_centered(draw, y_offset + 100, f"{stats['totalWords']:,}", value_font, (50, 0, 5), width)

    y_offset += 350

    # Longest fic card
    draw.rectangle([80, y_offset - 30, width - 80, y_offset + 340],
                  fill=(255, 245, 245), outline=(153, 0, 17), width=4)
    draw_text_centered(draw, y_offset + 20, "Longest Fic", label_font, (120, 0, 10), width)

    longest_text = f"{stats['longestFic']['wordCount']:,}"
    draw_text_centered(draw, y_offset + 100, longest_text, value_font, (50, 0, 5), width)

    words_font = get_font(40)
    draw_text_centered(draw, y_offset + 200, "words", words_font, (120, 0, 10), width)

    # Longest fic title
    if stats['longestFic']['title']:
        title_font_small = get_font(36)
        title_text = stats['longestFic']['title']
        title_lines = wrap_text(title_text, title_font_small, width - 180, draw)

        title_y = y_offset + 260
        for line in title_lines[:2]:
            draw_text_centered(draw, title_y, line, title_font_small, (90, 0, 8), width)
            title_y += 45

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
