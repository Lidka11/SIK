import laspy
import xml.etree.ElementTree as ET
import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon
from shapely.ops import unary_union
import matplotlib.pyplot as plt
import seaborn as sns

def odleglosc_punktu_od_plaszczyzny(punkt, a, b, c, d):
    x, y, z = punkt
    odleglosc = abs(a*x + b*y + c*z + d) / np.sqrt(a**2 + b**2 + c**2)
    return odleglosc

def srednia_odleglosc_od_plaszczyzny(cutted_points, roof_points, granica=1):
    x = roof_points[:, 0]
    y = roof_points[:, 1]
    z = roof_points[:, 2]
    # Zastosowanie metody najmniejszych kwadratów
    A = np.vstack([np.ones_like(x), x, y]).T
    b = z
    xplane = np.linalg.inv(A.T @ A) @ A.T @ b
    a, b, c = xplane
    A = b
    B = c
    C = -1
    D = a

    dobre_odleglosci = []
    for punkt in cutted_points:
        odleglosc = odleglosc_punktu_od_plaszczyzny(punkt, A, B, C, D)
        if odleglosc < granica:
            dobre_odleglosci.append(odleglosc)

    srednia = np.mean(dobre_odleglosci)
    return srednia


def bbox(roof_points):
    min_x = np.min(roof_points[:, 0])
    max_x = np.max(roof_points[:, 0])
    min_y = np.min(roof_points[:, 1])
    max_y = np.max(roof_points[:, 1])
    return min_x, max_x, min_y, max_y

def cut_roof(roof_point, cloud_xyz):
    min_x, max_x, min_y, max_y = bbox(roof_point)
    new_points=[]
    for point in cloud_xyz:
        if min_x <= point[0] <= max_x and min_y <= point[1] <= max_y:
            new_points.append(point)
    return np.array(new_points)



if __name__ == "__main__":
    # Ścieżki do plików
    las_path = r"lidar.laz"
    gml_path = r"budynek.gml"

    # Wczytanie pliku LAS/LAZ i filtrowanie punktów klasy "budynek" (klasa 6)
    points_cloud = laspy.read(las_path)
    building_mask = (points_cloud.classification == 6)
    building_points = points_cloud.points[building_mask]
    cloud_xyz = np.vstack((building_points.x, building_points.y, building_points.z)).transpose()

    # Wczytanie pliku GML
    tree = ET.parse(gml_path)
    root = tree.getroot()

    namespaces = {
        "gml": "http://www.opengis.net/gml",
        "bldg": "http://www.opengis.net/citygml/building/2.0"
    }

    roof_polygons = []

    # Wczytywanie punktów z dachów
    for roof_surface in root.findall(".//bldg:RoofSurface", namespaces):
        for lod2_multi_surface in roof_surface.findall(".//bldg:lod2MultiSurface", namespaces):
            polygon = lod2_multi_surface.find(".//gml:Polygon/gml:exterior/gml:LinearRing", namespaces)
            if polygon is not None:
                coords = polygon.findall("gml:pos", namespaces)
                polygon_coords = []
                for coord in coords:
                    coords_str = coord.text.split()
                    polygon_coords.append((float(coords_str[0]), float(coords_str[1]), float(coords_str[2])))
                roof_polygons.append(np.array(polygon_coords))

    roof_geometries = []
    # Przycinanie punktów chmury do dachów i wyświetlanie wyników
    srednie_wartosci = []
    for i, roof in enumerate(roof_polygons):
        cutted_points = cut_roof(roof, cloud_xyz)
        srednia = srednia_odleglosc_od_plaszczyzny(cutted_points, roof)
        srednia=srednia*100
        roof_geom=Polygon(roof)
        roof_geometries.append((roof_geom, srednia))
        srednie_wartosci.append(srednia)

    # Tworzenie wizualizacji     
    #1
    roof_df = gpd.GeoDataFrame(roof_geometries, columns=['geometry', 'avg_distance'])
    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    roof_df.plot(column='avg_distance', cmap='viridis', legend=True, ax=ax)
    ax.set_title('Średnie odległosci chmury punktów od płaszczyzny dachu')
    plt.show()
    #2
    srednia_wszystkich = np.mean(srednie_wartosci)
    roof_numbers = list(range(len(roof_polygons)))
    plt.figure(figsize=(10, 5))
    plt.bar(roof_numbers, srednie_wartosci, color='skyblue', label='Średnia odległość dla połaci')
    plt.axhline(y=srednia_wszystkich, color='red', linestyle='--', label=f'Średnia wszystkich: {srednia_wszystkich:.2f} cm')
    plt.xlabel('Numer połaci dachu')
    plt.ylabel('Średnia odległość (cm)')
    plt.title('Średnia odległość dla poszczególnych połaci dachu')
    plt.xticks(roof_numbers)
    plt.legend()
    plt.show()
