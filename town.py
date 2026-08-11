import csv
import math

import pygame

pygame.init()

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
TOOLBAR_HEIGHT = 60

GRID_SIZE = 20
ANGLE_STEP_DEGREES = 30
ENDPOINT_SNAP_RADIUS = 15
COLLINEAR_TOLERANCE = 2.0
OVERLAP_TOLERANCE = 0.5
CLICK_TOLERANCE = 4
HOVER_RADIUS = 8
MIN_INTERSECTION_SPACING = GRID_SIZE
EXPORT_PATH = "roads.csv"

BG_COLOR = (40, 44, 52)
GRID_COLOR = (55, 60, 70)
TOOLBAR_COLOR = (25, 28, 34)
BUTTON_COLOR = (70, 75, 85)
BUTTON_SELECTED_COLOR = (255, 255, 255)
TEXT_COLOR = (255, 255, 255)
TEXT_SELECTED_COLOR = (25, 28, 34)
ROAD_COLOR = (150, 155, 165)
ROAD_ENDPOINT_COLOR = (200, 205, 215)
PREVIEW_COLOR = (255, 210, 90)
HEX_MARKER_COLOR = (120, 200, 255)
HOVER_COLOR = (230, 70, 70)

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Town")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 28)
small_font = pygame.font.SysFont(None, 20)


class Button:
    def __init__(self, label, x, y, width, height, use_font=font):
        self.label = label
        self.rect = pygame.Rect(x, y, width, height)
        self.selected = False
        self.font = use_font

    def draw(self, surface):
        color = BUTTON_SELECTED_COLOR if self.selected else BUTTON_COLOR
        text_color = TEXT_SELECTED_COLOR if self.selected else TEXT_COLOR
        pygame.draw.rect(surface, color, self.rect, border_radius=6)
        text_surface = self.font.render(self.label, True, text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)


road_button = Button("Road", 10, 10, 100, 40)
select_button = Button("Select", 120, 10, 100, 40)
hexagon_button = Button("Hexagon", 230, 10, 100, 40)
tool_buttons = [road_button, select_button, hexagon_button]

angle_snap_button = Button("Snap 30°", 340, 6, 90, 24, use_font=small_font)
grid_snap_button = Button("Snap Grid", 340, 32, 90, 24, use_font=small_font)
angle_snap_button.selected = True
grid_snap_button.selected = True
toggle_buttons = [angle_snap_button, grid_snap_button]

export_button = Button("Export CSV", 690, 17, 100, 26, use_font=small_font)

STATUS_MESSAGE_DURATION_MS = 5000

selected_tool = None
roads = []
status_message = ""
status_message_expiry = 0

# Road drag state
drag_start = None
drag_end = None

# Hexagon placement state: "idle" -> "first_down" -> "awaiting_second_click" -> "second_down" -> "idle"
hex_state = "idle"
hex_first_vertex = None
hex_down_raw = None

hovered_road = None


def select_tool(button):
    global selected_tool
    for b in tool_buttons:
        b.selected = (b is button)
    selected_tool = button.label
    reset_hex_state()


def toggle(button):
    button.selected = not button.selected


def reset_hex_state():
    global hex_state, hex_first_vertex, hex_down_raw
    hex_state = "idle"
    hex_first_vertex = None
    hex_down_raw = None


def set_status(message, duration_ms=STATUS_MESSAGE_DURATION_MS):
    global status_message, status_message_expiry
    status_message = message
    status_message_expiry = pygame.time.get_ticks() + duration_ms


def clear_status():
    global status_message, status_message_expiry
    status_message = ""
    status_message_expiry = 0


def distance(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def points_close(a, b, tol=1.0):
    return distance(a, b) <= tol


def clamp_to_canvas(pos):
    return (max(pos[0], 0), max(pos[1], TOOLBAR_HEIGHT))


def snap_to_grid(pos):
    x, y = pos
    return (round(x / GRID_SIZE) * GRID_SIZE, round(y / GRID_SIZE) * GRID_SIZE)


def snap_to_angle(start, pos):
    dx, dy = pos[0] - start[0], pos[1] - start[1]
    dist = math.hypot(dx, dy)
    if dist == 0:
        return pos
    angle = math.atan2(dy, dx)
    step = math.radians(ANGLE_STEP_DEGREES)
    snapped_angle = round(angle / step) * step
    return (start[0] + dist * math.cos(snapped_angle), start[1] + dist * math.sin(snapped_angle))


def road_endpoints():
    for road in roads:
        yield road["start"]
        yield road["end"]


def find_nearby_endpoint(pos):
    nearest = None
    nearest_dist = ENDPOINT_SNAP_RADIUS
    for point in road_endpoints():
        d = distance(pos, point)
        if d <= nearest_dist:
            nearest = point
            nearest_dist = d
    return nearest


def resolve_point(pos, start=None):
    endpoint = find_nearby_endpoint(pos)
    if endpoint is not None:
        return endpoint
    result = pos
    if start is not None and angle_snap_button.selected:
        result = snap_to_angle(start, result)
    if grid_snap_button.selected:
        result = snap_to_grid(result)
    return result


def collinear(a, b, c):
    cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    length_ab = distance(a, b) or 1
    return abs(cross) / length_ab <= COLLINEAR_TOLERANCE


def try_merge_once(new_road):
    for road in roads:
        if points_close(road["end"], new_road["start"]):
            shared, far_existing, far_new = road["end"], road["start"], new_road["end"]
        elif points_close(road["start"], new_road["start"]):
            shared, far_existing, far_new = road["start"], road["end"], new_road["end"]
        elif points_close(road["end"], new_road["end"]):
            shared, far_existing, far_new = road["end"], road["start"], new_road["start"]
        elif points_close(road["start"], new_road["end"]):
            shared, far_existing, far_new = road["start"], road["end"], new_road["start"]
        else:
            continue
        if collinear(far_existing, shared, far_new):
            roads.remove(road)
            return {"start": far_existing, "end": far_new}
    return None


def normalize(vector):
    length = math.hypot(vector[0], vector[1])
    if length == 0:
        return (0.0, 0.0)
    return (vector[0] / length, vector[1] / length)


def project(point, origin, dir_unit):
    return (point[0] - origin[0]) * dir_unit[0] + (point[1] - origin[1]) * dir_unit[1]


def point_at(origin, dir_unit, t):
    return (origin[0] + dir_unit[0] * t, origin[1] + dir_unit[1] * t)


def subtract_overlaps(start, end):
    length = distance(start, end)
    if length == 0:
        return []
    dir_unit = normalize((end[0] - start[0], end[1] - start[1]))
    intervals = [(0.0, length)]
    for road in roads:
        q1, q2 = road["start"], road["end"]
        if not (collinear(start, end, q1) and collinear(start, end, q2)):
            continue
        t1 = project(q1, start, dir_unit)
        t2 = project(q2, start, dir_unit)
        lo, hi = min(t1, t2), max(t1, t2)
        remaining = []
        for a, b in intervals:
            overlap_lo, overlap_hi = max(a, lo), min(b, hi)
            if overlap_hi - overlap_lo <= OVERLAP_TOLERANCE:
                remaining.append((a, b))
                continue
            if overlap_lo - a > OVERLAP_TOLERANCE:
                remaining.append((a, overlap_lo))
            if b - overlap_hi > OVERLAP_TOLERANCE:
                remaining.append((overlap_hi, b))
        intervals = remaining
    return [
        (point_at(start, dir_unit, a), point_at(start, dir_unit, b))
        for a, b in intervals
        if b - a > OVERLAP_TOLERANCE
    ]


def segment_intersection(p1, p2, p3, p4):
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-9:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    u = ((x1 - x3) * (y1 - y2) - (y1 - y3) * (x1 - x2)) / denom
    if -1e-6 <= t <= 1 + 1e-6 and -1e-6 <= u <= 1 + 1e-6:
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
    return None


def existing_intersection_points():
    points = list(road_endpoints())
    for i in range(len(roads)):
        for j in range(i + 1, len(roads)):
            point = segment_intersection(
                roads[i]["start"], roads[i]["end"], roads[j]["start"], roads[j]["end"]
            )
            if point is not None:
                points.append(point)
    return points


def violates_min_spacing(start, end):
    new_points = [start, end]
    for road in roads:
        point = segment_intersection(start, end, road["start"], road["end"])
        if point is not None:
            new_points.append(point)
    for new_point in new_points:
        for existing_point in existing_intersection_points():
            gap = distance(new_point, existing_point)
            if 1.0 < gap < MIN_INTERSECTION_SPACING:
                return True
    return False


def add_merged_segment(start, end):
    if points_close(start, end):
        return
    new_road = {"start": start, "end": end}
    while True:
        merged = try_merge_once(new_road)
        if merged is None:
            break
        new_road = merged
    roads.append(new_road)
    clear_status()


def add_road(start, end):
    if points_close(start, end):
        return
    if violates_min_spacing(start, end):
        set_status("Road rejected: too close to an existing intersection")
        return
    for seg_start, seg_end in subtract_overlaps(start, end):
        add_merged_segment(seg_start, seg_end)


def compute_hexagon_vertices(v1, v2):
    if points_close(v1, v2):
        return None
    center = ((v1[0] + v2[0]) / 2, (v1[1] + v2[1]) / 2)
    radius = distance(v1, v2) / 2
    angle0 = math.atan2(v1[1] - center[1], v1[0] - center[0])
    vertices = []
    for k in range(6):
        angle = angle0 + math.radians(60 * k)
        vx = center[0] + radius * math.cos(angle)
        vy = center[1] + radius * math.sin(angle)
        vertices.append(snap_to_grid((vx, vy)))
    return vertices


def create_hexagon(v1, v2):
    vertices = compute_hexagon_vertices(v1, v2)
    if vertices is None:
        return
    for i in range(6):
        add_road(vertices[i], vertices[(i + 1) % 6])


def export_roads_to_csv():
    with open(EXPORT_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["road_id", "start_x", "start_y", "end_x", "end_y"])
        for i, road in enumerate(roads):
            sx, sy = road["start"]
            ex, ey = road["end"]
            writer.writerow([i, round(sx, 2), round(sy, 2), round(ex, 2), round(ey, 2)])
    set_status("Exported {} road(s) to {}".format(len(roads), EXPORT_PATH))


def draw_grid(surface):
    for x in range(0, SCREEN_WIDTH, GRID_SIZE):
        pygame.draw.line(surface, GRID_COLOR, (x, TOOLBAR_HEIGHT), (x, SCREEN_HEIGHT))
    for y in range(TOOLBAR_HEIGHT, SCREEN_HEIGHT, GRID_SIZE):
        pygame.draw.line(surface, GRID_COLOR, (0, y), (SCREEN_WIDTH, y))


def draw_roads(surface):
    for road in roads:
        pygame.draw.line(surface, ROAD_COLOR, road["start"], road["end"], 6)
        pygame.draw.circle(surface, ROAD_ENDPOINT_COLOR, road["start"], 4)
        pygame.draw.circle(surface, ROAD_ENDPOINT_COLOR, road["end"], 4)


def point_segment_distance(point, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        return distance(point, a)
    t = ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / length_sq
    t = max(0.0, min(1.0, t))
    closest = (a[0] + t * dx, a[1] + t * dy)
    return distance(point, closest)


def find_hovered_road(pos):
    nearest = None
    nearest_dist = HOVER_RADIUS
    for road in roads:
        d = point_segment_distance(pos, road["start"], road["end"])
        if d <= nearest_dist:
            nearest = road
            nearest_dist = d
    return nearest


def draw_hex_preview(surface):
    if hex_state == "idle" or hex_first_vertex is None:
        return
    pygame.draw.circle(surface, HEX_MARKER_COLOR, hex_first_vertex, 5)
    mouse_pos = clamp_to_canvas(pygame.mouse.get_pos())
    live_second = snap_to_grid(mouse_pos)
    vertices = compute_hexagon_vertices(hex_first_vertex, live_second)
    if vertices is not None:
        pygame.draw.polygon(surface, PREVIEW_COLOR, vertices, 2)
    else:
        pygame.draw.line(surface, PREVIEW_COLOR, hex_first_vertex, live_second, 2)


running = True
while running:
    mouse_pos = pygame.mouse.get_pos()
    if selected_tool == "Select" and mouse_pos[1] > TOOLBAR_HEIGHT:
        hovered_road = find_hovered_road(mouse_pos)
    else:
        hovered_road = None

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_BACKSPACE, pygame.K_DELETE) and hovered_road is not None:
                roads.remove(hovered_road)
                hovered_road = None
                set_status("Deleted road")

        elif event.type == pygame.MOUSEBUTTONDOWN:
            clicked_ui = False
            for button in tool_buttons:
                if button.is_clicked(event.pos):
                    select_tool(button)
                    clicked_ui = True
            for button in toggle_buttons:
                if button.is_clicked(event.pos):
                    toggle(button)
                    clicked_ui = True
            if export_button.is_clicked(event.pos):
                export_roads_to_csv()
                clicked_ui = True

            if not clicked_ui and event.pos[1] > TOOLBAR_HEIGHT:
                if selected_tool == "Road":
                    drag_start = resolve_point(event.pos)
                    drag_end = drag_start
                elif selected_tool == "Hexagon":
                    pos = clamp_to_canvas(event.pos)
                    if hex_state == "idle":
                        hex_first_vertex = snap_to_grid(pos)
                        hex_down_raw = event.pos
                        hex_state = "first_down"
                    elif hex_state == "awaiting_second_click":
                        hex_down_raw = event.pos
                        hex_state = "second_down"

        elif event.type == pygame.MOUSEBUTTONUP:
            if drag_start is not None:
                pos = clamp_to_canvas(event.pos)
                final_end = resolve_point(pos, start=drag_start)
                add_road(drag_start, final_end)
                drag_start = None
                drag_end = None

            if hex_state == "first_down":
                pos = clamp_to_canvas(event.pos)
                if distance(event.pos, hex_down_raw) <= CLICK_TOLERANCE:
                    hex_state = "awaiting_second_click"
                else:
                    opposite_vertex = snap_to_grid(pos)
                    create_hexagon(hex_first_vertex, opposite_vertex)
                    reset_hex_state()
            elif hex_state == "second_down":
                pos = clamp_to_canvas(event.pos)
                opposite_vertex = snap_to_grid(pos)
                create_hexagon(hex_first_vertex, opposite_vertex)
                reset_hex_state()

        elif event.type == pygame.MOUSEMOTION:
            if drag_start is not None:
                pos = clamp_to_canvas(event.pos)
                drag_end = resolve_point(pos, start=drag_start)

    if status_message and pygame.time.get_ticks() >= status_message_expiry:
        clear_status()

    screen.fill(BG_COLOR)
    draw_grid(screen)
    if hovered_road is not None:
        pygame.draw.line(screen, HOVER_COLOR, hovered_road["start"], hovered_road["end"], 12)
    draw_roads(screen)

    if drag_start is not None and drag_end is not None:
        pygame.draw.line(screen, PREVIEW_COLOR, drag_start, drag_end, 3)

    draw_hex_preview(screen)

    toolbar_rect = pygame.Rect(0, 0, SCREEN_WIDTH, TOOLBAR_HEIGHT)
    pygame.draw.rect(screen, TOOLBAR_COLOR, toolbar_rect)

    for button in tool_buttons:
        button.draw(screen)
    for button in toggle_buttons:
        button.draw(screen)
    export_button.draw(screen)

    if status_message:
        status_surface = small_font.render(status_message, True, TEXT_COLOR)
        screen.blit(status_surface, (450, 22))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
