import pygame
import random
import time
import math

SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 600

PLAYING = 0
TRUCK_HIT = 1
GAME_OVER = 2

pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("C-RAM_simulator")
clock = pygame.time.Clock()

c_ram = pygame.transform.scale_by(pygame.image.load("c-ram.png"), 1.5)
truck_mount = pygame.transform.scale_by(pygame.image.load("truck_mount.png"), 1.5)
bullet_img = pygame.transform.scale_by(pygame.image.load("bullet.png"), 2)
background = pygame.transform.scale_by(pygame.image.load("background.png"), 1)
jet_img = pygame.transform.scale_by(pygame.image.load("jet.png"), 0.5)
helicopter_img = pygame.transform.scale_by(pygame.image.load("helicopter.png"), 0.5)
explosion_img = pygame.transform.scale_by(pygame.image.load("explosion.png"), 0.5)
infantry_truck_img_original = pygame.transform.scale_by(pygame.image.load("infantry_truck.png"), 0.1)
infantry_truck_img = infantry_truck_img_original.copy()
missile_img = pygame.transform.scale_by(pygame.image.load("missile.png"), 0.75)
bomb_img = pygame.transform.scale_by(pygame.image.load("bomb.png"), 2)
small_explosion_img = pygame.transform.scale_by(pygame.image.load("small_explosion.png"), 0.15)
firing_sound = pygame.mixer.Sound("firing.wav")
small_explosion_sound = pygame.mixer.Sound("small_explosion_sound.mp3")
firing_channel = pygame.mixer.Channel(0)

c_ram_pivot_offset = (27, 33)
c_ram_barrel_offset = (0, 31)
rotation = 0
truck_pivot_point = (551, 554)
bullets = []
bullet_speed = 20
last_spawn = time.time()
spawn_frequency = 1
enemies = []
bombs = []
velocity = 0
barrel_heat = 0
heat_cap = 50
overheat_cooldown = 75
overheating = False
overheat_counter = 0
bullet_spread = 1
jet_speed = 10
helicopter_speed = 7
shooting_rotation_speed = 1
not_shooting_rotation_speed = 3
target_x = 95
missile_bomb_speed = 6
bomb_bomb_speed = 2
missile_rotation_speed = 1
bomb_rotation_speed = 0.75
turret_is_firing = False
overheating_circle_rect = pygame.Rect(440, SCREEN_HEIGHT - 40, 35, 35)

game_state = PLAYING
truck_death_counter = 0
score = 0

infantry_truck_rect = infantry_truck_img.get_rect()
infantry_truck_rect.x = 30
infantry_truck_rect.y = SCREEN_HEIGHT - infantry_truck_img.get_height()

def get_c_ram_topleft():
    rotated_c_ram = pygame.transform.rotate(c_ram, rotation)
    rotated_rect = rotated_c_ram.get_rect()
    original_center = pygame.math.Vector2(c_ram.get_width() / 2, c_ram.get_height() / 2)
    pivot_from_center = pygame.math.Vector2(c_ram_pivot_offset) - original_center
    rotated_pivot_from_center = pivot_from_center.rotate(-rotation)
    pivot_in_rotated = pygame.math.Vector2(rotated_rect.center) + rotated_pivot_from_center
    top_left = (
        truck_pivot_point[0] - pivot_in_rotated.x,
        truck_pivot_point[1] - pivot_in_rotated.y
    )
    return top_left, rotated_c_ram

def get_barrel_tip(top_left):
    rotated_rect = pygame.transform.rotate(c_ram, rotation).get_rect()
    original_center = pygame.math.Vector2(c_ram.get_width() / 2, c_ram.get_height() / 2)
    barrel_from_center = pygame.math.Vector2(c_ram_barrel_offset) - original_center
    rotated_barrel_from_center = barrel_from_center.rotate(-rotation)
    barrel_in_rotated = pygame.math.Vector2(rotated_rect.center) + rotated_barrel_from_center
    return (top_left[0] + barrel_in_rotated.x, top_left[1] + barrel_in_rotated.y)

def shoot():
    rect = bullet_img.get_rect()
    x = barrel_pos[0] - bullet_img.get_width() / 2
    y = barrel_pos[1] - bullet_img.get_height() / 2
    rect.x = x
    rect.y = y
    bullets.append({"rect": rect, "rotation": rotation + random.uniform(-bullet_spread, bullet_spread), "x": x, "y": y})

def release_bomb(x,y,bombtype):
    rect = missile_img.get_rect() if bombtype == "missile" else bomb_img.get_rect()
    rect.x = x
    rect.y = y
    dist_to_target_hor = x - target_x
    if dist_to_target_hor == 0:
        dist_to_target_hor = 0.001
    dist_to_target_vert = SCREEN_HEIGHT - y - infantry_truck_img.get_height()
    vert_speed_bomb = dist_to_target_vert / dist_to_target_hor
    bomb_max_rotation = math.degrees(math.atan(vert_speed_bomb)) if bombtype == "missile" else 90
    bombs.append({"rect": rect,"bomb_type": bombtype,"vert_speed": vert_speed_bomb,"bomb_current_rotation": 0,"bomb_max_rotation": bomb_max_rotation,"deathcounter": -1})

def spawn():
    global last_spawn
    if time.time() - last_spawn >= spawn_frequency:
        if random.randint(1,2) == 1:
            bomb_type = random.choice(["missile","bomb"])
            bomb_release = random.randint(500,850) if bomb_type == "missile" else random.randint(250,320)
            enemies.append({"rect":jet_img.get_rect(),"image": jet_img,"bomb_type": bomb_type,"speed": jet_speed,"x": SCREEN_WIDTH + jet_img.get_width(),"y": random.randint(50,300),"deathcounter": -1,"bomb_release": bomb_release,"bomb_released_yet": False})
        else:
            enemies.append({"rect":helicopter_img.get_rect(),"image": helicopter_img,"speed": helicopter_speed,"x": SCREEN_WIDTH + helicopter_img.get_width(),"y": random.randint(150,300),"deathcounter": -1,"bomb_release": random.randint(700,850),"bomb_type": "missile","bomb_released_yet": False})
        last_spawn = time.time()

def draw_overheat_arc():
    if overheating:
        pygame.draw.arc(screen, (255, 0, 0), overheating_circle_rect, 0, 360, width=10)
    else:
        pygame.draw.arc(screen, (255, 255, 255), overheating_circle_rect, 0, math.radians(7.2 * barrel_heat), width=10)

def reset_game():
    global enemies, bullets, bombs, barrel_heat, overheating, overheat_counter
    global infantry_truck_img, game_state, score, truck_death_counter
    enemies = []
    bullets = []
    bombs = []
    barrel_heat = 0
    overheating = False
    overheat_counter = 0
    infantry_truck_img = infantry_truck_img_original.copy()
    game_state = PLAYING
    score = 0
    truck_death_counter = 0

font_big = pygame.font.Font("Jersey10.ttf", 80)
font_small = pygame.font.Font("Jersey10.ttf", 40)

running = True
while running:
    screen.blit(background, (0,0))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN and game_state == GAME_OVER:
            if play_again_rect.collidepoint(event.pos):
                reset_game()

    keys = pygame.key.get_pressed()

    if game_state != GAME_OVER:
        spawn()

        if keys[pygame.K_LEFT]:
            rotation += shooting_rotation_speed if turret_is_firing else not_shooting_rotation_speed
        if keys[pygame.K_RIGHT]:
            rotation -= shooting_rotation_speed if turret_is_firing else not_shooting_rotation_speed
        rotation = max(-172, min(rotation, 0))

        top_left, rotated_c_ram = get_c_ram_topleft()
        barrel_pos = get_barrel_tip(top_left)

        if keys[pygame.K_UP] and not overheating and game_state == PLAYING:
            shoot()
            turret_is_firing = True
        else:
            turret_is_firing = False
#overheat
        if turret_is_firing and not firing_channel.get_busy():
            firing_channel.play(firing_sound, loops=-1)
        if not turret_is_firing:
            firing_channel.fadeout(200)

        if turret_is_firing:
            barrel_heat += 1
        else:
            barrel_heat = max(0, barrel_heat - 2)

        if barrel_heat >= heat_cap:
            overheat_counter = overheat_cooldown
            overheating = True
        if overheating:
            overheat_counter -= 1
            if overheat_counter <= 0:
                overheating = False
                barrel_heat = 15

        #pygame.draw.rect(screen, (255, 0, 0), infantry_truck_rect, 1)

        for enemy in enemies[:]:
            enemy["rect"].x = enemy["x"]
            enemy["rect"].y = enemy["y"]
            if enemy["deathcounter"] < 0:
                enemy["x"] -= enemy["speed"]
            if enemy["rect"].x + enemy["image"].get_width() < 0:
                enemies.remove(enemy)
            screen.blit(enemy["image"], enemy["rect"])
            if enemy["rect"].x <= enemy["bomb_release"] and not enemy["bomb_released_yet"]:
                release_bomb(enemy["rect"].x, enemy["rect"].bottom, enemy["bomb_type"])
                enemy["bomb_released_yet"] = True

        for bullet in bullets[:]:
            for enemy in enemies[:]:
                if bullet["rect"].colliderect(enemy["rect"]) and enemy["deathcounter"] < 0:
                    bullets.remove(bullet)
                    enemy["deathcounter"] = 8
                    small_explosion_sound.play()
                    score += 100

        for enemy in enemies[:]:
            if enemy["deathcounter"] == 0:
                enemies.remove(enemy)
            elif enemy["deathcounter"] > 0:
                enemy["deathcounter"] -= 1
                enemy["image"] = small_explosion_img

        for bullet in bullets[:]:
            bullet["x"] -= math.cos(math.radians(bullet["rotation"])) * bullet_speed
            bullet["y"] += math.sin(math.radians(bullet["rotation"])) * bullet_speed
            bullet["rect"].x = bullet["x"]
            bullet["rect"].y = bullet["y"]
            if bullet["rect"].x < 0 or bullet["rect"].x > SCREEN_WIDTH or bullet["rect"].y < 0 or bullet["rect"].y > SCREEN_HEIGHT:
                bullets.remove(bullet)
            else:
                screen.blit(pygame.transform.rotate(bullet_img, bullet["rotation"]), bullet["rect"])

        for bomb in bombs[:]:
            if bomb["rect"].colliderect(infantry_truck_rect) and game_state == PLAYING:
                game_state = TRUCK_HIT
                truck_death_counter = 60
                bombs.clear()

            for bullet in bullets[:]:
                if bomb["rect"].colliderect(bullet["rect"]) and bomb["deathcounter"] < 0:
                    bomb["deathcounter"] = 8
                    bullets.remove(bullet)
                    score += 50

        for bomb in bombs[:]:
            if bomb["deathcounter"] == 0:
                bombs.remove(bomb)
            elif bomb["deathcounter"] > 0:
                bomb["deathcounter"] -= 1

        for bomb in bombs[:]:
            if bomb["bomb_type"] == "missile":
                if bomb["deathcounter"] < 0:
                    bomb["rect"].x -= missile_bomb_speed
                    bomb["rect"].y += bomb["vert_speed"] * missile_bomb_speed
                if bomb["bomb_current_rotation"] < bomb["bomb_max_rotation"]:
                    bomb["bomb_current_rotation"] += missile_rotation_speed
                img = pygame.transform.rotate(missile_img, bomb["bomb_current_rotation"])
            else:
                if bomb["deathcounter"] < 0:
                    bomb["rect"].x -= bomb_bomb_speed
                    bomb["rect"].y += bomb["vert_speed"] * bomb_bomb_speed
                if bomb["bomb_current_rotation"] < bomb["bomb_max_rotation"]:
                    bomb["bomb_current_rotation"] += bomb_rotation_speed
                img = pygame.transform.rotate(bomb_img, bomb["bomb_current_rotation"])
            if bomb["deathcounter"] > 0:
                screen.blit(small_explosion_img, bomb["rect"])
            else:
                screen.blit(img, bomb["rect"])

    if game_state == TRUCK_HIT:
        infantry_truck_img = explosion_img
        truck_death_counter -= 1
        if truck_death_counter <= 0:
            game_state = GAME_OVER
    top_left, rotated_c_ram = get_c_ram_topleft()
    screen.blit(rotated_c_ram, top_left)
    screen.blit(truck_mount, (480, SCREEN_HEIGHT - truck_mount.get_height()))
    screen.blit(infantry_truck_img, (30, SCREEN_HEIGHT - infantry_truck_img.get_height()))
    draw_overheat_arc()

    if game_state == GAME_OVER:
        game_over_text = font_big.render("GAME OVER", True, (255,0,0))
        score_text = font_small.render(f"Score: {score}", True, (255,255,255))
        play_again_rect = pygame.Rect(SCREEN_WIDTH//2 - 100, 400, 200, 60)
        pygame.draw.rect(screen, (255,255,255), play_again_rect, border_radius=4)
        play_again_text = font_small.render("Play Again", True, (0,0,0))
        screen.blit(game_over_text, (SCREEN_WIDTH//2 - game_over_text.get_width() / 2, 200))
        screen.blit(score_text, (SCREEN_WIDTH//2 - score_text.get_width() / 2, 300))
        screen.blit(play_again_text, (SCREEN_WIDTH//2 - play_again_text.get_width() / 2 + 2, 407))

    pygame.display.update()
    clock.tick(60)