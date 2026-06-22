# HidroMira

Sistema IoT para el monitoreo continuo y análisis de vibraciones en la hidroturbina de la Central Hidroeléctrica Mira.

## Descripción

HidroMira es una plataforma tecnológica orientada a la supervisión y análisis del comportamiento vibracional de equipos hidroeléctricos mediante sensores IoT, procesamiento de datos y visualización en tiempo real.

El sistema permite la adquisición continua de datos, almacenamiento histórico, generación de alertas y análisis de tendencias para apoyar la detección temprana de anomalías y la toma de decisiones en actividades de mantenimiento predictivo.

## Objetivos

* Monitorear continuamente las vibraciones de la hidroturbina.
* Registrar y almacenar datos históricos para análisis posterior.
* Identificar comportamientos anómalos en el funcionamiento del equipo.
* Facilitar el mantenimiento predictivo mediante indicadores y alertas.
* Proporcionar visualización de datos en tiempo real a través de una plataforma web.

## Características

* Adquisición de datos mediante sensores IoT.
* Comunicación en tiempo real.
* Almacenamiento de series temporales.
* Panel web para monitoreo.
* Visualización de gráficos e indicadores.
* Gestión de usuarios y roles.
* Generación de alertas por umbrales configurables.
* Exportación de reportes.

## Arquitectura

Sistema compuesto por:

* Capa de Sensores IoT
* Gateway de Comunicación
* Backend de Procesamiento
* Base de Datos
* API REST
* Plataforma Web de Monitoreo

## Tecnologías Utilizadas

### Hardware

* Sensores de vibración
* Microcontroladores ESP32
* Infraestructura de red

### Software

* Python
* Django
* MariaDB
* MQTT
* JavaScript
* HTML5 y CSS3
* Docker

## Estructura del Proyecto

```text
hidromira/
├── backend/
├── frontend/
├── api/
├── database/
├── docs/
├── firmware/
├── tests/
└── deployment/
```

## Instalación

### Clonar el repositorio

```bash
git clone https://github.com/Computacion-UPEC/HidroMira.git
cd HidroMira
```

### Instalar dependencias

```bash
pip install -r requirements.txt
```

### Configurar variables de entorno

```env
DB_HOST=localhost
DB_NAME=hidromira
DB_USER=user
DB_PASSWORD=password
```

### Ejecutar el proyecto

```bash
python manage.py runserver
```

## Casos de Uso

* Monitoreo de hidroturbinas.
* Detección temprana de fallas mecánicas.
* Mantenimiento predictivo.
* Investigación académica.
* Análisis de vibraciones industriales.

## Equipo de Desarrollo

Proyecto desarrollado por estudiantes e investigadores de la Carrera de Computación de la Universidad Politécnica Estatal del Carchi (UPEC).

## Estado del Proyecto

🚧 En desarrollo## 
by Geovanny Basantes 2026
## Licencia

Este proyecto se distribuye bajo la licencia MIT.
