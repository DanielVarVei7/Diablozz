import mysql.connector

conexion=mysql.connector.connect(
    host="bw6edd5vgbde6c1thfqc-mysql.services.clever-cloud.com",
user="uhk2k7vwn1h9wkti",
password="E6zMg7mODitydpDeRD27",
database="bw6edd5vgbde6c1thfqc")

if conexion.is_connected():
    print("Conexion Exitosa")