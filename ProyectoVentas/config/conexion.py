import mysql.connector

conexion=mysql.connector.connect(
    host="localhost",
user="root",
password="1234",
database="bdventas")

if conexion.is_connected():
    print("Conexion Exitosa")