Generowanie modelu siatkowego LOD 1

Opis projektu

Niniejszy projekt realizuje zadanie półautomatycznego generowania modelu siatkowego w standardzie zbliżonym do CityGML LOD-1 na podstawie danych przestrzennych.

Dane wejściowe

-  Warstwa wektorowa (hextiles.fgb) zawierająca siatkę sześciokątnych kafelków
  
-  Dane pobierane z GUGIK:
  
-  Numeryczny Model Terenu (NMT)
  
-  Numeryczny Model Pokrycia Terenu (NMPT)
  
-  Dane BDOT (BUBD_A).

Projekt obejmuje dwa skrypty A i B.
Co robi skrypt A?
✅ Pobiera i przetwarza dane NMPT, NMT oraz BDOT10k
✅ Przycina je do obszaru wybranego kafelka
✅ Łączy rastry NMPT i NMT
✅ Tworzy plik geopackage z budynkami

Co robi skrypt B?
✅ Wczytuje dane NMT, NMPT oraz BDOT10k
✅ Tworzy model 3D terenu na podstawie rastra NMT
✅ Ekstruduje budynki na podstawie wysokości z NMPT i NMT
✅ Łączy teren i budynki w jeden model 3D
✅ Wizualizuje i zapisuje wynik jako plik .ply

Przykład:
![image](https://github.com/user-attachments/assets/74ee0233-2333-41de-8ad0-06741fd73a41)
