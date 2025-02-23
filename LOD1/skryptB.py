import geopandas as gpd
import open3d.visualization
from pathlib import Path
from osgeo import gdal
import numpy as np
import open3d
from shapely.geometry import Polygon



def read_raster(filename):
    raster = gdal.Open(filename)
    return raster


def create_vertex_array(raster):
    transform = raster.GetGeoTransform()
    width = raster.RasterXSize
    height = raster.RasterYSize
    x = np.arange(0, width) * transform[1] + transform[0]
    y = np.arange(0, height) * transform[5] + transform[3]
    xx, yy = np.meshgrid(x, y)
    zz = raster.ReadAsArray()
    vertices = np.vstack((xx, yy, zz)).reshape([3, -1]).transpose()
    return vertices


def create_index_array(raster):
    width = raster.RasterXSize
    height = raster.RasterYSize

    ai = np.arange(0, width - 1)
    aj = np.arange(0, height - 1)
    aii, ajj = np.meshgrid(ai, aj)
    a = aii + ajj * width
    a = a.flatten()

    tria = np.vstack((a, a + width, a + width + 1, a, a + width + 1, a + 1))
    tria = np.transpose(tria).reshape([-1, 3])
    return tria




def draw_mesh():
    mesh: open3d.geometry.TriangleMesh = open3d.geometry.TriangleMesh.create_sphere()
    mesh.compute_vertex_normals()
    open3d.visualization.draw_geometries(
        [mesh]
    )


def save_mesh():
    mesh = open3d.geometry.TriangleMesh.create_sphere()
    mesh.compute_vertex_normals()
    open3d.io.write_triangle_mesh("mesh.ply", mesh)


def extrude_polygon(buildinggeometry, min_height, max_height):
    polygon = buildinggeometry
    xy = polygon.exterior.coords
    xy = list(xy[:-1])
    xy = np.float64(xy)
    centroid = np.float64(polygon.representative_point().xy).flatten()

    base_num_vertices = xy.shape[0]
    xyz = np.vstack([
        np.hstack([
            xy, np.full((xy.shape[0], 1), min_height)
        ]),
        np.hstack([
            xy, np.full((xy.shape[0], 1), max_height)
        ]),
        np.hstack([centroid, min_height]),
        np.hstack([centroid, max_height])
    ])

    walls_triangles = []
    for i in range(base_num_vertices - 1):
        walls_triangles.append(
            [i, i + 1, i + 1 + base_num_vertices][::-1]
        )
        walls_triangles.append(
            [i + 1 + base_num_vertices, i + base_num_vertices, i][::-1]
        )
    walls_triangles.append(
        [base_num_vertices - 1, 0, base_num_vertices][::-1]
    )
    walls_triangles.append(
        [base_num_vertices, 2 * base_num_vertices - 1, base_num_vertices - 1][::-1]
    )

    base_triangles = []
    for i in range(base_num_vertices - 1):
        base_triangles.append(
            [i, 2 * base_num_vertices, i + 1][::-1]
        )
        base_triangles.append(
            [base_num_vertices + i, 2 * base_num_vertices + 1, base_num_vertices + i + 1]
        )
    base_triangles.append(
        [base_num_vertices - 1, 2 * base_num_vertices, 0][::-1]
    )
    base_triangles.append(
        [2 * base_num_vertices - 1, 2 * base_num_vertices + 1, base_num_vertices]
    )

    mesh = open3d.geometry.TriangleMesh(
        open3d.utility.Vector3dVector(xyz),
        open3d.utility.Vector3iVector(base_triangles + walls_triangles)
    )
    mesh.compute_vertex_normals()
    mesh.paint_uniform_color([0.0, 0.6, 0.0])
    return mesh


def get_building_heights(building_geometry, nmt_raster, nmpt_raster):
    representative_point = building_geometry.representative_point()
    x, y = representative_point.x, representative_point.y
    base_height = raster_sample(nmt_raster, x, y) or 0
    building_height = raster_sample(nmpt_raster, x, y) or 0
    min_height = base_height  
    max_height = base_height + building_height  
    return min_height, max_height


def raster_sample(raster, x, y):
    transform = raster.GetGeoTransform()
    x_off = int((x - transform[0]) / transform[1])
    y_off = int((y - transform[3]) / transform[5])
    band = raster.GetRasterBand(1)
    value = band.ReadAsArray(x_off, y_off, 1, 1)

    if value[0][0] == band.GetNoDataValue():
        return None
    return value[0][0]
 
if __name__ == '__main__':
    path = Path(__file__).parent / "hextiles.fgb"
    tiles = gpd.read_file(str(path))
    index=23
    tile= tiles.iloc[[index]]
    bbox= tile.total_bounds
    bbbox= bbox
    bbox=[bbox[0], bbox[1], bbox[2], bbox[3]]
    bbox=tuple(bbox)

    buildingd_w_gpkg_url = r"downloaded/bdot10k_bubd_a/clipped_BUBD_A.gpkg"
    raster_nmpt = read_raster(r"output_nmpt.tif")
    raster_nmt= read_raster(r"output_nmt.tif")
    vertices = create_vertex_array(raster_nmt)
    triangles = create_index_array(raster_nmt)
    mesh = open3d.geometry.TriangleMesh(
        open3d.utility.Vector3dVector(vertices),
        open3d.utility.Vector3iVector(triangles)
    )
    mesh.compute_vertex_normals()
    buildings_gdf = gpd.read_file(buildingd_w_gpkg_url)
    all_building_mesh = open3d.geometry.TriangleMesh()
    building_meshes = []
    for index, building in buildings_gdf.iterrows():
        if not isinstance(building.geometry, Polygon):
            continue  
        min_height, max_height = get_building_heights(building.geometry, raster_nmt, raster_nmt)
        building_mesh = extrude_polygon(building.geometry, min_height, max_height)
        if building_mesh is not None:
            all_building_mesh += building_mesh
    mesh_nmt_buildings = mesh + all_building_mesh
    mesh_nmt_buildings.compute_vertex_normals()
    open3d.visualization.draw_geometries([mesh_nmt_buildings])
    open3d.io.write_triangle_mesh("zad2/nmt_buildings_mesh.ply", mesh_nmt_buildings)

