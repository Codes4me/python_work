import csv
import math

import pygame

pygame.init()

SCREEN_WIDTH = 900
SCREEN_HEIGHT = 600
TOOLBAR_HEIGHT = 140

GRID_SIZE = 20
ANGLE_STEP_DEGREES = 30
ENDPOINT_SNAP_RADIUS = 15
COLLINEAR_TOLERANCE = 2.0
OVERLAP_TOLERANCE = 0.5
CLICK_TOLERANCE = 4
HOVER_RADIUS = 8
MIN_INTERSECTION_SPACING = GRID_SIZE
ROAD_HOVER_THRESHOLD = 30
PREFERRED_HOUSE_WIDTH = 3
MIN_HOUSE_WIDTH = 1
MAX_HOUSE_WIDTH = 5
HOUSE_DEPTH_SQUARES = 2
PREFERRED_BUSINESS_WIDTH = 7
MIN_BUSINESS_WIDTH = 4
MAX_BUSINESS_WIDTH = 10
BUSINESS_DEPTH_SQUARES = 2
ROAD_DRAW_WIDTH = GRID_SIZE * 2
PATH_DRAW_WIDTH = GRID_SIZE * 1
ROAD_HOUSE_CLEARANCE = GRID_SIZE // 2
MIN_PARK_SQUARES = 5
EXPORT_PATH = "roads.csv"

# Demand generated per square of residential built, relative to 49.6 residential squares
SERVICE_DEMAND_RATIO = 7.75 / 49.6
COMMERCIAL_DEMAND_RATIO = 11.4 / 49.6
INDUSTRIAL_DEMAND_RATIO = 13.2 / 49.6
POPULATION_PER_RESIDENTIAL_SQUARE = 0.16

RESIDENTIAL_TAX_PER_CAPITA = 45.0
COMMERCIAL_TAX_PER_SQUARE = 3.0
INDUSTRIAL_TAX_PER_SQUARE = 2.5
SERVICE_TAX_PER_SQUARE = 2.75
STREET_UPKEEP_PER_SQUARE = 1.5
PATH_UPKEEP_PER_SQUARE = 0.5

BG_COLOR = (40, 44, 52)
GRID_COLOR = (55, 60, 70)
TOOLBAR_COLOR = (25, 28, 34)
BUTTON_COLOR = (70, 75, 85)
BUTTON_SELECTED_COLOR = (255, 255, 255)
TEXT_COLOR = (255, 255, 255)
TEXT_SELECTED_COLOR = (25, 28, 34)
ROAD_COLOR = (150, 155, 165)
PATH_COLOR = (170, 160, 130)
ROAD_ENDPOINT_COLOR = (200, 205, 215)
PREVIEW_COLOR = (255, 210, 90)
HEX_MARKER_COLOR = (120, 200, 255)
HOVER_COLOR = (230, 70, 70)
HOUSE_COLOR = (190, 140, 90)
HOUSE_OUTLINE_COLOR = (120, 85, 50)
COMMERCIAL_COLOR = (90, 130, 190)
COMMERCIAL_OUTLINE_COLOR = (50, 80, 130)
INDUSTRIAL_COLOR = (200, 170, 70)
INDUSTRIAL_OUTLINE_COLOR = (140, 110, 30)
SERVICE_COLOR = (150, 110, 180)
SERVICE_OUTLINE_COLOR = (95, 65, 120)
PARK_COLOR = (70, 130, 80)
PARK_OUTLINE_COLOR = (35, 90, 45)
STATUS_BG_COLOR = (15, 17, 21)
DEMAND_OK_COLOR = (60, 100, 65)
DEMAND_SHORT_COLOR = (110, 45, 45)
POPULATION_BG_COLOR = (55, 60, 80)

BUILDING_STYLE = {
    "residential": (HOUSE_COLOR, HOUSE_OUTLINE_COLOR),
    "commercial": (COMMERCIAL_COLOR, COMMERCIAL_OUTLINE_COLOR),
    "industrial": (INDUSTRIAL_COLOR, INDUSTRIAL_OUTLINE_COLOR),
    "service": (SERVICE_COLOR, SERVICE_OUTLINE_COLOR),
}

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


street_button = Button("Street", 6, 6, 80, 40, use_font=small_font)
path_button = Button("Path", 90, 6, 80, 40, use_font=small_font)
select_button = Button("Select", 174, 6, 80, 40, use_font=small_font)
hexagon_button = Button("Hexagon", 258, 6, 80, 40, use_font=small_font)
houses_button = Button("Houses", 342, 6, 80, 40, use_font=small_font)
park_button = Button("Park", 426, 6, 80, 40, use_font=small_font)
commercial_button = Button("Commercial", 510, 6, 80, 40, use_font=small_font)
industrial_button = Button("Industrial", 594, 6, 80, 40, use_font=small_font)
service_button = Button("Service", 678, 6, 80, 40, use_font=small_font)
tool_buttons = [
    street_button, path_button, select_button, hexagon_button, houses_button,
    park_button, commercial_button, industrial_button, service_button,
]

angle_snap_button = Button("Snap 30°", 766, 6, 90, 24, use_font=small_font)
grid_snap_button = Button("Snap Grid", 766, 32, 90, 24, use_font=small_font)
angle_snap_button.selected = True
grid_snap_button.selected = True
toggle_buttons = [angle_snap_button, grid_snap_button]

export_button = Button("Export CSV", 634, 62, 100, 26, use_font=small_font)
import_button = Button("Import CSV", 744, 62, 100, 26, use_font=small_font)

STATUS_MESSAGE_DURATION_MS = 5000

selected_tool = None
roads = []
buildings = []
parks = []
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
hovered_building = None
hovered_park = None


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
        if road["type"] != new_road["type"]:
            continue
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
            return {"start": far_existing, "end": far_new, "type": new_road["type"]}
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


def add_merged_segment(start, end, road_type="street"):
    if points_close(start, end):
        return
    new_road = {"start": start, "end": end, "type": road_type}
    while True:
        merged = try_merge_once(new_road)
        if merged is None:
            break
        new_road = merged
    roads.append(new_road)
    road_polygon = road_to_polygon(new_road)
    destroyed = [b for b in buildings if polygons_overlap(b["corners"], road_polygon, tol=0)]
    for building in destroyed:
        buildings.remove(building)
    if road_type == "street":
        recalculate_parks_for_polygon(road_polygon)
    if destroyed:
        refresh_all_parks()
        set_status("Placed {} and removed {} building(s)".format(road_type, len(destroyed)))
    else:
        clear_status()


def add_road(start, end, road_type="street"):
    if points_close(start, end):
        return
    if violates_min_spacing(start, end):
        set_status("Road rejected: too close to an existing intersection")
        return
    for seg_start, seg_end in subtract_overlaps(start, end):
        add_merged_segment(seg_start, seg_end, road_type)


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


def compute_house_widths(total_squares):
    if total_squares <= 0:
        return []
    candidate_widths = [w for w in range(MIN_HOUSE_WIDTH + 1, MAX_HOUSE_WIDTH + 1)]
    candidate_widths.sort(key=lambda w: (abs(w - PREFERRED_HOUSE_WIDTH), w))
    for width in candidate_widths:
        if total_squares % width == 0:
            return [width] * (total_squares // width)
    full_count = total_squares // PREFERRED_HOUSE_WIDTH
    remainder = total_squares % PREFERRED_HOUSE_WIDTH
    widths = [PREFERRED_HOUSE_WIDTH] * full_count
    if remainder > 0:
        widths.append(remainder)
    return widths


def compute_business_widths(total_squares, min_width, max_width, preferred_width):
    if total_squares < min_width:
        return []
    candidate_widths = list(range(min_width, max_width + 1))
    candidate_widths.sort(key=lambda w: (abs(w - preferred_width), w))
    for width in candidate_widths:
        if total_squares % width == 0:
            return [width] * (total_squares // width)
    full_count = total_squares // preferred_width
    remainder = total_squares % preferred_width
    widths = [preferred_width] * full_count
    if remainder >= min_width:
        widths.append(remainder)
    elif remainder > 0 and widths and widths[-1] + remainder <= max_width:
        widths[-1] += remainder
    return widths


def project_polygon(polygon, axis):
    dots = [p[0] * axis[0] + p[1] * axis[1] for p in polygon]
    return min(dots), max(dots)


def polygons_overlap(poly_a, poly_b, tol=OVERLAP_TOLERANCE):
    for polygon in (poly_a, poly_b):
        for i in range(len(polygon)):
            p1, p2 = polygon[i], polygon[(i + 1) % len(polygon)]
            axis = normalize((-(p2[1] - p1[1]), p2[0] - p1[0]))
            min_a, max_a = project_polygon(poly_a, axis)
            min_b, max_b = project_polygon(poly_b, axis)
            if max_a <= min_b + tol or max_b <= min_a + tol:
                return False
    return True


def road_width(road):
    return PATH_DRAW_WIDTH if road.get("type") == "path" else ROAD_DRAW_WIDTH


def road_to_polygon(road, width=None):
    if width is None:
        width = road_width(road)
    start, end = road["start"], road["end"]
    dir_unit = normalize((end[0] - start[0], end[1] - start[1]))
    perp = (-dir_unit[1], dir_unit[0])
    half = width / 2
    offset = (perp[0] * half, perp[1] * half)
    return [
        (start[0] + offset[0], start[1] + offset[1]),
        (end[0] + offset[0], end[1] + offset[1]),
        (end[0] - offset[0], end[1] - offset[1]),
        (start[0] - offset[0], start[1] - offset[1]),
    ]


def find_road_near(pos, threshold=ROAD_HOVER_THRESHOLD, road_type=None):
    nearest = None
    nearest_dist = threshold
    for road in roads:
        if road_type is not None and road["type"] != road_type:
            continue
        d = point_segment_distance(pos, road["start"], road["end"])
        if d <= nearest_dist:
            nearest = road
            nearest_dist = d
    return nearest


BUILDING_LABELS = {
    "residential": "house",
    "commercial": "commercial building",
    "industrial": "industrial building",
    "service": "service building",
}


def place_building_along_road(road, click_pos, kind, min_width, max_width, depth_squares, width_fn):
    label = BUILDING_LABELS[kind]
    start, end = road["start"], road["end"]
    length = distance(start, end)
    total_squares = math.floor(length / GRID_SIZE)
    if total_squares < min_width:
        set_status("Road too short for a {}".format(label))
        return
    dir_unit = normalize((end[0] - start[0], end[1] - start[1]))
    perp = (-dir_unit[1], dir_unit[0])
    to_click = (click_pos[0] - start[0], click_pos[1] - start[1])
    if to_click[0] * perp[0] + to_click[1] * perp[1] < 0:
        perp = (-perp[0], -perp[1])
    depth_px = depth_squares * GRID_SIZE
    edge_offset = road_width(road) / 2
    edge_start = (start[0] + perp[0] * edge_offset, start[1] + perp[1] * edge_offset)

    def conflicts(corners):
        return any(polygons_overlap(corners, existing["corners"]) for existing in buildings) or any(
            polygons_overlap(corners, road_to_polygon(other_road), tol=ROAD_HOUSE_CLEARANCE)
            for other_road in roads
            if other_road is not road
        )

    def corners_for(width_squares):
        width_px = width_squares * GRID_SIZE
        near1 = point_at(edge_start, dir_unit, offset)
        near2 = point_at(edge_start, dir_unit, offset + width_px)
        far2 = (near2[0] + perp[0] * depth_px, near2[1] + perp[1] * depth_px)
        far1 = (near1[0] + perp[0] * depth_px, near1[1] + perp[1] * depth_px)
        return [near1, near2, far2, far1]

    widths_squares = width_fn(total_squares)
    offset = 0.0
    placed_count = 0
    skipped_count = 0
    for width_squares in widths_squares:
        chosen_width = None
        chosen_corners = None
        for candidate_width in range(width_squares, min_width - 1, -1):
            corners = corners_for(candidate_width)
            if not conflicts(corners):
                chosen_width = candidate_width
                chosen_corners = corners
                break
        if chosen_width is None:
            skipped_count += 1
        else:
            buildings.append({
                "corners": chosen_corners, "kind": kind,
                "width_squares": chosen_width, "depth_squares": depth_squares,
            })
            recalculate_parks_for_polygon(chosen_corners)
            placed_count += 1
        offset += width_squares * GRID_SIZE

    if placed_count == 0:
        set_status("No {}s placed: space already occupied".format(label))
    elif skipped_count > 0:
        set_status("Placed {} {}(s), skipped {} (overlap)".format(placed_count, label, skipped_count))
    else:
        set_status("Placed {} {}(s)".format(placed_count, label))


def place_houses_along_road(road, click_pos):
    place_building_along_road(
        road, click_pos, "residential", MIN_HOUSE_WIDTH, MAX_HOUSE_WIDTH, HOUSE_DEPTH_SQUARES,
        compute_house_widths,
    )


def place_business_along_road(road, click_pos, kind):
    place_building_along_road(
        road, click_pos, kind, MIN_BUSINESS_WIDTH, MAX_BUSINESS_WIDTH, BUSINESS_DEPTH_SQUARES,
        lambda total: compute_business_widths(total, MIN_BUSINESS_WIDTH, MAX_BUSINESS_WIDTH, PREFERRED_BUSINESS_WIDTH),
    )


def residential_squares_total():
    return sum(b["width_squares"] * b["depth_squares"] for b in buildings if b["kind"] == "residential")


def compute_demand():
    residential_squares = residential_squares_total()
    supply = {"service": 0, "commercial": 0, "industrial": 0}
    for b in buildings:
        if b["kind"] in supply:
            supply[b["kind"]] += b["width_squares"] * b["depth_squares"]
    demand = {
        "service": residential_squares * SERVICE_DEMAND_RATIO,
        "commercial": residential_squares * COMMERCIAL_DEMAND_RATIO,
        "industrial": residential_squares * INDUSTRIAL_DEMAND_RATIO,
    }
    return demand, supply


def compute_population():
    return residential_squares_total() * POPULATION_PER_RESIDENTIAL_SQUARE


def draw_demand_row(surface):
    demand, supply = compute_demand()
    x, y = 6, 62

    population_rect = pygame.Rect(x, y, 110, 26)
    pygame.draw.rect(surface, POPULATION_BG_COLOR, population_rect, border_radius=4)
    population_surface = small_font.render("Pop: {:.1f}".format(compute_population()), True, TEXT_COLOR)
    surface.blit(population_surface, population_surface.get_rect(center=population_rect.center))
    x += 110 + 8

    badge_width = 160
    for kind in ("service", "commercial", "industrial"):
        met = supply[kind] >= demand[kind]
        bg_color = DEMAND_OK_COLOR if met else DEMAND_SHORT_COLOR
        label = "{}: {:.1f}/{:.1f}".format(kind.capitalize(), supply[kind], demand[kind])
        rect = pygame.Rect(x, y, badge_width, 26)
        pygame.draw.rect(surface, bg_color, rect, border_radius=4)
        text_surface = small_font.render(label, True, TEXT_COLOR)
        text_rect = text_surface.get_rect(center=rect.center)
        surface.blit(text_surface, text_rect)
        x += badge_width + 10


def compute_income():
    _, supply = compute_demand()
    population = compute_population()
    residential_tax = population * RESIDENTIAL_TAX_PER_CAPITA
    commercial_tax = supply["commercial"] * COMMERCIAL_TAX_PER_SQUARE
    industrial_tax = supply["industrial"] * INDUSTRIAL_TAX_PER_SQUARE
    service_tax = supply["service"] * SERVICE_TAX_PER_SQUARE
    revenue = residential_tax + commercial_tax + industrial_tax + service_tax

    street_squares = sum(
        math.floor(distance(r["start"], r["end"]) / GRID_SIZE) for r in roads if r["type"] == "street"
    )
    path_squares = sum(
        math.floor(distance(r["start"], r["end"]) / GRID_SIZE) for r in roads if r["type"] == "path"
    )
    upkeep = street_squares * STREET_UPKEEP_PER_SQUARE + path_squares * PATH_UPKEEP_PER_SQUARE

    return revenue, upkeep, revenue - upkeep


def draw_income_row(surface):
    revenue, upkeep, net = compute_income()
    bg_color = DEMAND_OK_COLOR if net >= 0 else DEMAND_SHORT_COLOR
    label = "Net Income: {}${:.2f}  (Tax ${:.2f} - Upkeep ${:.2f})".format(
        "+" if net >= 0 else "-", abs(net), revenue, upkeep
    )
    rect = pygame.Rect(6, 96, SCREEN_WIDTH - 12, 30)
    pygame.draw.rect(surface, bg_color, rect, border_radius=4)
    text_surface = small_font.render(label, True, TEXT_COLOR)
    surface.blit(text_surface, text_surface.get_rect(center=rect.center))


def cell_polygon(col, row):
    x0, y0 = col * GRID_SIZE, row * GRID_SIZE
    x1, y1 = x0 + GRID_SIZE, y0 + GRID_SIZE
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def cell_in_bounds(col, row):
    x0, y0 = col * GRID_SIZE, row * GRID_SIZE
    return (
        x0 >= 0
        and y0 >= TOOLBAR_HEIGHT
        and x0 + GRID_SIZE <= SCREEN_WIDTH
        and y0 + GRID_SIZE <= SCREEN_HEIGHT
    )


def cell_free_for_park(col, row, extra_blocked=frozenset()):
    if not cell_in_bounds(col, row):
        return False
    if (col, row) in extra_blocked:
        return False
    poly = cell_polygon(col, row)
    if any(polygons_overlap(poly, b["corners"], tol=0) for b in buildings):
        return False
    if any(
        road["type"] == "street" and polygons_overlap(poly, road_to_polygon(road), tol=0)
        for road in roads
    ):
        return False
    return not any((col, row) in park["cells"] for park in parks)


def cell_touches_road(col, row):
    cx = col * GRID_SIZE + GRID_SIZE / 2
    cy = row * GRID_SIZE + GRID_SIZE / 2
    for road in roads:
        threshold = road_width(road) / 2 + GRID_SIZE / 2 + 1
        if point_segment_distance((cx, cy), road["start"], road["end"]) <= threshold:
            return True
    return False


def cells_adjacent(cells_a, cells_b):
    for c, r in cells_a:
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (c + dc, r + dr) in cells_b:
                return True
    return False


def grow_park_region(seed_col, seed_row):
    if not cell_free_for_park(seed_col, seed_row):
        return None
    region = {(seed_col, seed_row)}
    frontier = [(seed_col, seed_row)]
    while frontier:
        col, row = frontier.pop()
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            neighbor = (col + dc, row + dr)
            if neighbor in region:
                continue
            if cell_free_for_park(neighbor[0], neighbor[1]):
                region.add(neighbor)
                frontier.append(neighbor)
    if len(region) < MIN_PARK_SQUARES * MIN_PARK_SQUARES:
        return None
    return region


def place_park(click_pos):
    seed_col = int(click_pos[0] // GRID_SIZE)
    seed_row = int(click_pos[1] // GRID_SIZE)
    cells = grow_park_region(seed_col, seed_row)
    if cells is None:
        set_status("Not enough space for a park (needs at least {}x{})".format(
            MIN_PARK_SQUARES, MIN_PARK_SQUARES
        ))
        return
    if not any(cell_touches_road(c, r) for c, r in cells):
        set_status("Park needs street or path access")
        return
    merged_cells = set(cells)
    merged_origins = {(seed_col, seed_row)}
    for park in list(parks):
        if cells_adjacent(cells, park["cells"]):
            merged_cells |= park["cells"]
            merged_origins |= park["origins"]
            parks.remove(park)
    parks.append({"cells": merged_cells, "origins": merged_origins})
    clear_status()


def recalculate_park(park):
    park["cells"] = set()
    new_cells = set()
    surviving_origins = set()
    for origin in park["origins"]:
        result = grow_park_region(*origin)
        if result is not None:
            new_cells |= result
            surviving_origins.add(origin)
    if not new_cells:
        parks.remove(park)
    else:
        park["cells"] = new_cells
        park["origins"] = surviving_origins


def recalculate_parks_for_polygon(polygon):
    for park in list(parks):
        if any(polygons_overlap(cell_polygon(*cell), polygon, tol=0) for cell in park["cells"]):
            recalculate_park(park)


def refresh_all_parks():
    for park in list(parks):
        recalculate_park(park)


def find_hovered_park(pos):
    col = int(pos[0] // GRID_SIZE)
    row = int(pos[1] // GRID_SIZE)
    for park in parks:
        if (col, row) in park["cells"]:
            return park
    return None


def format_points(points):
    return ";".join("{}:{}".format(round(x, 2), round(y, 2)) for x, y in points)


def export_roads_to_csv():
    with open(EXPORT_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["kind", "id", "part", "detail", "points"])
        for i, road in enumerate(roads):
            writer.writerow(["road", i, 0, road["type"], format_points([road["start"], road["end"]])])
        for i, building in enumerate(buildings):
            writer.writerow(["building", i, 0, building["kind"], format_points(building["corners"])])
        for i, park in enumerate(parks):
            cell_list = ";".join("{}:{}".format(c, r) for c, r in sorted(park["cells"]))
            writer.writerow(["park", i, 0, "", cell_list])
    set_status("Exported {} road(s), {} building(s), {} park(s) to {}".format(
        len(roads), len(buildings), len(parks), EXPORT_PATH
    ))


def parse_points(points_str):
    points = []
    for pair in points_str.split(";"):
        if not pair:
            continue
        x_str, y_str = pair.split(":")
        points.append((float(x_str), float(y_str)))
    return points


def import_town_from_csv():
    try:
        f = open(EXPORT_PATH, newline="")
    except FileNotFoundError:
        set_status("No {} found to import".format(EXPORT_PATH))
        return

    new_roads = []
    new_buildings = []
    park_cells_by_id = {}
    with f:
        reader = csv.DictReader(f)
        for row in reader:
            kind = row["kind"]
            if kind == "road":
                points = parse_points(row["points"])
                if len(points) < 2:
                    continue
                new_roads.append({"start": points[0], "end": points[1], "type": row["detail"]})
            elif kind == "building":
                points = parse_points(row["points"])
                if len(points) < 4:
                    continue
                width_px = distance(points[0], points[1])
                depth_px = distance(points[1], points[2])
                new_buildings.append({
                    "corners": points,
                    "kind": row["detail"],
                    "width_squares": max(1, round(width_px / GRID_SIZE)),
                    "depth_squares": max(1, round(depth_px / GRID_SIZE)),
                })
            elif kind == "park":
                cells = set()
                for pair in row["points"].split(";"):
                    if not pair:
                        continue
                    c_str, r_str = pair.split(":")
                    cells.add((int(c_str), int(r_str)))
                park_cells_by_id.setdefault(row["id"], set()).update(cells)

    roads.clear()
    roads.extend(new_roads)
    buildings.clear()
    buildings.extend(new_buildings)
    parks.clear()
    for cells in park_cells_by_id.values():
        if not cells:
            continue
        parks.append({"cells": cells, "origins": {next(iter(cells))}})

    reset_hex_state()
    global selected_tool
    for button in tool_buttons:
        button.selected = False
    selected_tool = None

    set_status("Imported {} road(s), {} building(s), {} park(s) from {}".format(
        len(roads), len(buildings), len(parks), EXPORT_PATH
    ))


def draw_grid(surface):
    for x in range(0, SCREEN_WIDTH, GRID_SIZE):
        pygame.draw.line(surface, GRID_COLOR, (x, TOOLBAR_HEIGHT), (x, SCREEN_HEIGHT))
    for y in range(TOOLBAR_HEIGHT, SCREEN_HEIGHT, GRID_SIZE):
        pygame.draw.line(surface, GRID_COLOR, (0, y), (SCREEN_WIDTH, y))


def draw_roads(surface):
    for road in roads:
        color = PATH_COLOR if road["type"] == "path" else ROAD_COLOR
        pygame.draw.line(surface, color, road["start"], road["end"], road_width(road))
        pygame.draw.circle(surface, ROAD_ENDPOINT_COLOR, road["start"], 4)
        pygame.draw.circle(surface, ROAD_ENDPOINT_COLOR, road["end"], 4)


def draw_buildings(surface):
    for building in buildings:
        fill_color, outline_color = BUILDING_STYLE[building["kind"]]
        pygame.draw.polygon(surface, fill_color, building["corners"])
        pygame.draw.polygon(surface, outline_color, building["corners"], 2)


def draw_parks(surface):
    for park in parks:
        cells = park["cells"]
        for col, row in cells:
            x0, y0 = col * GRID_SIZE, row * GRID_SIZE
            pygame.draw.rect(surface, PARK_COLOR, pygame.Rect(x0, y0, GRID_SIZE, GRID_SIZE))
            x1, y1 = x0 + GRID_SIZE, y0 + GRID_SIZE
            if (col, row - 1) not in cells:
                pygame.draw.line(surface, PARK_OUTLINE_COLOR, (x0, y0), (x1, y0), 2)
            if (col, row + 1) not in cells:
                pygame.draw.line(surface, PARK_OUTLINE_COLOR, (x0, y1), (x1, y1), 2)
            if (col - 1, row) not in cells:
                pygame.draw.line(surface, PARK_OUTLINE_COLOR, (x0, y0), (x0, y1), 2)
            if (col + 1, row) not in cells:
                pygame.draw.line(surface, PARK_OUTLINE_COLOR, (x1, y0), (x1, y1), 2)


def point_segment_distance(point, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        return distance(point, a)
    t = ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / length_sq
    t = max(0.0, min(1.0, t))
    closest = (a[0] + t * dx, a[1] + t * dy)
    return distance(point, closest)


def buildings_on_road(road):
    start, end = road["start"], road["end"]
    edge_tolerance = road_width(road) / 2 + OVERLAP_TOLERANCE
    return [
        building
        for building in buildings
        if point_segment_distance(building["corners"][0], start, end) <= edge_tolerance
        and point_segment_distance(building["corners"][1], start, end) <= edge_tolerance
    ]


def find_hovered_road(pos):
    nearest = None
    nearest_dist = HOVER_RADIUS
    for road in roads:
        d = point_segment_distance(pos, road["start"], road["end"])
        if d <= nearest_dist:
            nearest = road
            nearest_dist = d
    return nearest


def point_in_polygon(point, polygon):
    side = None
    for i in range(len(polygon)):
        a, b = polygon[i], polygon[(i + 1) % len(polygon)]
        edge = (b[0] - a[0], b[1] - a[1])
        to_point = (point[0] - a[0], point[1] - a[1])
        cross = edge[0] * to_point[1] - edge[1] * to_point[0]
        if abs(cross) < 1e-9:
            continue
        current_side = cross > 0
        if side is None:
            side = current_side
        elif current_side != side:
            return False
    return True


def find_hovered_building(pos):
    for building in buildings:
        if point_in_polygon(pos, building["corners"]):
            return building
    return None


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
        hovered_building = find_hovered_building(mouse_pos)
        hovered_road = None if hovered_building is not None else find_hovered_road(mouse_pos)
        hovered_park = None if (hovered_building is not None or hovered_road is not None) else find_hovered_park(mouse_pos)
    else:
        hovered_road = None
        hovered_building = None
        hovered_park = None

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_BACKSPACE, pygame.K_DELETE):
                if hovered_building is not None:
                    buildings.remove(hovered_building)
                    hovered_building = None
                    refresh_all_parks()
                    set_status("Deleted building")
                elif hovered_road is not None:
                    attached_buildings = buildings_on_road(hovered_road)
                    for building in attached_buildings:
                        buildings.remove(building)
                    roads.remove(hovered_road)
                    hovered_road = None
                    refresh_all_parks()
                    if attached_buildings:
                        set_status("Deleted road and {} building(s)".format(len(attached_buildings)))
                    else:
                        set_status("Deleted road")
                elif hovered_park is not None:
                    parks.remove(hovered_park)
                    hovered_park = None
                    set_status("Deleted park")

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
            if import_button.is_clicked(event.pos):
                import_town_from_csv()
                clicked_ui = True

            if not clicked_ui and event.pos[1] > TOOLBAR_HEIGHT:
                if selected_tool in ("Street", "Path"):
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
                elif selected_tool == "Houses":
                    target_road = find_road_near(event.pos)
                    if target_road is None:
                        set_status("No road nearby to place houses on")
                    elif target_road["type"] == "path":
                        set_status("Can't place houses on a path")
                    else:
                        place_houses_along_road(target_road, event.pos)
                elif selected_tool in ("Commercial", "Industrial", "Service"):
                    kind = selected_tool.lower()
                    target_road = find_road_near(event.pos)
                    if target_road is None:
                        set_status("No road nearby to place a {} building on".format(kind))
                    elif target_road["type"] == "path":
                        set_status("Can't place a {} building on a path".format(kind))
                    else:
                        place_business_along_road(target_road, event.pos, kind)
                elif selected_tool == "Park":
                    place_park(event.pos)

        elif event.type == pygame.MOUSEBUTTONUP:
            if drag_start is not None:
                pos = clamp_to_canvas(event.pos)
                final_end = resolve_point(pos, start=drag_start)
                road_type = "path" if selected_tool == "Path" else "street"
                add_road(drag_start, final_end, road_type)
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
    draw_parks(screen)
    if hovered_park is not None:
        for cell in hovered_park["cells"]:
            pygame.draw.rect(screen, HOVER_COLOR, pygame.Rect(
                cell[0] * GRID_SIZE, cell[1] * GRID_SIZE, GRID_SIZE, GRID_SIZE
            ), 2)
    draw_buildings(screen)
    draw_roads(screen)
    if hovered_road is not None:
        border_polygon = road_to_polygon(hovered_road, width=road_width(hovered_road) + 6)
        pygame.draw.polygon(screen, HOVER_COLOR, border_polygon, 3)
    if hovered_building is not None:
        pygame.draw.polygon(screen, HOVER_COLOR, hovered_building["corners"], 4)

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
    import_button.draw(screen)
    draw_demand_row(screen)
    draw_income_row(screen)

    if status_message:
        status_surface = small_font.render(status_message, True, TEXT_COLOR)
        padding = 8
        bg_rect = status_surface.get_rect(topleft=(padding, padding)).inflate(padding, padding)
        pygame.draw.rect(screen, STATUS_BG_COLOR, bg_rect, border_radius=4)
        screen.blit(status_surface, (padding, padding))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
