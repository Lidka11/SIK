import geopandas as gpd
import shapely
from pathlib import Path
from owslib.wfs import WebFeatureService
import requests
import rasterio
from rasterio.plot import show
from http.client import RemoteDisconnected
from pathlib import Path
from time import sleep
from typing import Union
from osgeo import gdal
import requests
from owslib.feature.wfs100 import WebFeatureService_1_0_0
from owslib.feature.wfs110 import WebFeatureService_1_1_0
from owslib.feature.wfs200 import WebFeatureService_2_0_0
from owslib.wfs import WebFeatureService
from io import BytesIO
from zipfile import ZipFile
import rasterio
from rasterio.mask import mask
import shapely
import requests
from zipfile import ZipFile
from io import BytesIO
WfsType = Union[WebFeatureService_1_0_0, WebFeatureService_1_1_0, WebFeatureService_2_0_0]


def download_and_save_file(download_url: str, save_path: Union[Path, str]) -> None:
    response = requests.get(download_url)

    if response.status_code != 200:
        raise Exception(f"Failed to download {download_url}. Status code: {response.status_code}")

    with open(save_path, "wb") as file:
        file.write(response.content)


def wfs_connect_to_service(wfs_url: str, version: str = '1.0.0', number_of_retries: int = 10) -> WfsType:
    wfs_service = None
    for _ in range(number_of_retries):
        try:
            wfs_service = WebFeatureService(url=wfs_url, version=version)
        except (ConnectionError, RemoteDisconnected):
            sleep(1)
        else:
            break

    if wfs_service is None:
        raise Exception(f"Failed to communicate with WFS service {wfs_url}")

    return wfs_service



if __name__ == '__main__':
    path = Path(__file__).parent / "hextiles.fgb"
    tiles = gpd.read_file(str(path))
    index=23
    tile= tiles.iloc[[index]]

    bbox= tile.total_bounds
    bbbox= bbox
    bbox=[bbox[0], bbox[1], bbox[2], bbox[3]]
    bbox=tuple(bbox)

    #pobieranie danych z nmpt
    nmpt_url="https://mapy.geoportal.gov.pl/wss/service/PZGIK/NumerycznyModelPokryciaTerenuEVRF2007/WFS/Skorowidze"
    nmpt_wfs= wfs_connect_to_service(nmpt_url, version='2.0.0')
    nmpt_response=nmpt_wfs.getfeature(
        bbox=bbox,
        typename=["gugik:SkorowidzNMPT2023"]
    )
    with open("downloaded/nmpt.xml", "wb") as file:
        file.write(nmpt_response.read())
    nmpt_sections = gpd.read_file("downloaded/nmpt.xml")
    nmpt_url_save = nmpt_sections["url_do_pobrania"].iloc[0]
    download_and_save_file(nmpt_url_save, "downloaded/nmpt.asc")

    nmpt_response_22=nmpt_wfs.getfeature(
        bbox=bbox,
        typename=["gugik:SkorowidzNMPT2022"]
    )
    with open("downloaded/nmpt_22.xml", "wb") as file:
        file.write(nmpt_response_22.read())
    nmpt_sections = gpd.read_file("downloaded/nmpt_22.xml")
    nmpt_url_save = nmpt_sections["url_do_pobrania"].iloc[0]
    download_and_save_file(nmpt_url_save, "downloaded/nmpt_22.asc")

    #przycinanie nmpt do kafelka
    with rasterio.open("downloaded/nmpt.asc") as src:
        out_image, out_transform = mask(src, tile.geometry, crop=True)
        out_meta = src.meta
    out_meta.update({"driver": "GTiff",
                     "height": out_image.shape[1],
                     "width": out_image.shape[2],
                     "transform": out_transform})
    output_file = 'masked_nmpt23.tif'
    with rasterio.open(output_file, "w", **out_meta) as dest:
        dest.write(out_image)
    with rasterio.open("downloaded/nmpt_22.asc") as src:
        out_image, out_transform = mask(src, tile.geometry, crop=True)
        out_meta = src.meta
    out_meta.update({"driver": "GTiff",
                     "height": out_image.shape[1],
                     "width": out_image.shape[2],
                     "transform": out_transform})
    output_file = 'masked_nmpt22.tif'
    with rasterio.open(output_file, "w", **out_meta) as dest:
        dest.write(out_image)

    file1="masked_nmpt23.tif"
    file2="masked_nmpt22.tif"
    
    #polaczenie 2 czesci kafelka
    files_to_mosaic = ["masked_nmpt23.tif", "masked_nmpt22.tif"] 
    g = gdal.Warp("output_nmpt.tif", files_to_mosaic, format="GTiff",
                options=["COMPRESS=LZW", "TILED=YES"])
    g = None 

    #pobranie danych z nmt
    nmt_url = "https://mapy.geoportal.gov.pl/wss/service/PZGIK/NumerycznyModelTerenuEVRF2007/WFS/Skorowidze"
    nmt_wfs= wfs_connect_to_service(nmt_url, version='2.0.0')
    nmt_response=nmt_wfs.getfeature(
        bbox=bbox,
        typename=["gugik:SkorowidzNMT2023"]
    )
    with open("downloaded/nmt.xml", "wb") as file:
        file.write(nmt_response.read())

    nmt_sections = gpd.read_file("downloaded/nmt.xml")
    nmt_url_save = nmt_sections["url_do_pobrania"].iloc[0]
    download_and_save_file(nmt_url_save, "downloaded/nmt.asc")

    #przyciecie nmt do kafelka
    with rasterio.open("downloaded/nmt.asc") as src:
        out_image, out_transform = mask(src, tile.geometry, crop=True)
        out_meta = src.meta
        out_meta.update({"driver": "GTiff",
                        "height": out_image.shape[1],
                        "width": out_image.shape[2],
                        "transform": out_transform})
        output_file = 'masked_nmt.tif'
        with rasterio.open(output_file, "w", **out_meta) as dest:
            dest.write(out_image)
  
    #przesuniecie bboxa w celu pobrania drugiej czesci kafelka
    new_bbox = [bbox[0]-1000, bbox[1], bbox[2]-1000, bbox[3]]
    new_bbox = tuple(new_bbox)
    print(bbox)

    #pobranie nmt i przyciecie nmt
    nmt_url = "https://mapy.geoportal.gov.pl/wss/service/PZGIK/NumerycznyModelTerenuEVRF2007/WFS/Skorowidze"
    nmt_wfs= wfs_connect_to_service(nmt_url, version='2.0.0')
    nmt_response=nmt_wfs.getfeature(
        bbox=new_bbox,
        typename=["gugik:SkorowidzNMT2023"]
    )
    with open("downloaded/nmtl.xml", "wb") as file:
        file.write(nmt_response.read())

    nmt_sections = gpd.read_file("downloaded/nmtl.xml")
    nmt_url_save = nmt_sections["url_do_pobrania"].iloc[0]
    download_and_save_file(nmt_url_save, "downloaded/nmtl.asc")
    with rasterio.open("downloaded/nmtl.asc") as src:
        out_image, out_transform = mask(src, tile.geometry, crop=True)
        out_meta = src.meta
        out_meta.update({"driver": "GTiff",
                        "height": out_image.shape[1],
                        "width": out_image.shape[2],
                        "transform": out_transform})
        output_file = 'masked_nmtl.tif'
        with rasterio.open(output_file, "w", **out_meta) as dest:
            dest.write(out_image)

    #polaczenie 2 czesci kafelka i stworzenie jednego rastra 
    files_to_mosaic1 = ["masked_nmt.tif", "masked_nmtl.tif"]
    g = gdal.Warp("output_nmt.tif", files_to_mosaic1, format="GTiff",
                options=["COMPRESS=LZW", "TILED=YES"])
    g = None 


    #pobranie pliku zip z budynkami dla powiatu malborskiego
    bdot10k_url = "https://opendata.geoportal.gov.pl/bdot10k/schemat2021/22/2209_GML.zip"
    response = requests.get(bdot10k_url)
    zip_content = BytesIO(response.content)
    with ZipFile(zip_content) as zipfile:
            zip_files = zipfile.namelist()
            filtered_files = [f for f in zip_files if "BUBD_A" in f]
            for file in filtered_files:
                zipfile.extract(file, "downloaded/bdot10k_bubd_a")


    #zapis budynkow z bubda do pliku gpkg
    path = r"C:\sem 4\Standardy 3D\cwicz1\downloaded\bdot10k_bubd_a\PL.PZGiK.336.2209\BDOT10k\PL.PZGiK.336.2209__OT_BUBD_A.gml"
    buildings = gpd.read_file(str(path))
    buildings_clipped = buildings.clip(tile, keep_geom_type=True)
    output_file_path = r"downloaded/bdot10k_bubd_a/clipped_BUBD_A.gpkg"
    buildings_clipped = buildings_clipped.applymap(lambda x: str(x) if isinstance(x, list) else x)
    buildings_clipped.to_file(output_file_path)
