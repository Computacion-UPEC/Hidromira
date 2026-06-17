#include <Servo.h>

// Definición de Pines de Arduino
const int ENA_PIN = 9;      // Pin de velocidad PWM para L298N (puente H). ¡Conéctalo a ENA si quieres regular la potencia!
const int IN1_PIN = 8;      // Dirección 1 del L298N
const int IN2_PIN = 7;      // Dirección 2 del L298N
const int SERVO_PIN = 11;   // Pin de control para el Servomotor

Servo myServo;              // Instancia de la librería Servo
String inputString = "";    // Buffer para almacenar el comando recibido
bool stringComplete = false;// Indicador de comando recibido completo

void setup() {
  // Inicialización del puerto serial a 9600 baudios
  Serial.begin(9600);
  
  // Configuración de pines del puente H L298N como salidas
  pinMode(ENA_PIN, OUTPUT);
  pinMode(IN1_PIN, OUTPUT);
  pinMode(IN2_PIN, OUTPUT);
  
  // Parar el motor inicialmente por seguridad
  digitalWrite(IN1_PIN, LOW);
  digitalWrite(IN2_PIN, LOW);
  analogWrite(ENA_PIN, 0);
  
  // Conectar y centrar el servomotor a 95 grados (posición inicial de tu código)
  myServo.attach(SERVO_PIN);
  myServo.write(95);
  
  // Reservar 50 bytes para el búfer del comando serial
  inputString.reserve(50);
  
  // Mensaje de éxito en la inicialización
  Serial.println("INIT_OK: Sistema de control iniciado. Listo para comandos.");
}

void loop() {
  // Verificar si hay un comando completo (que terminó con salto de línea '\n')
  if (stringComplete) {
    inputString.trim(); // Eliminar espacios en blanco y saltos de línea sobrantes
    
    if (inputString.length() > 0) {
      char cmdType = inputString.charAt(0);   // Primer caracter: comando (S o M)
      String valueStr = inputString.substring(1); // Resto del texto: valor numérico
      int value = valueStr.toInt();
      
      if (cmdType == 'S' || cmdType == 's') {
        // Comando de Servo (Rango del código original: 10 a 100 grados)
        value = constrain(value, 10, 100);
        myServo.write(value);
        Serial.print("ACK: Servo ajustado a ");
        Serial.println(value);
      } 
      else if (cmdType == 'M' || cmdType == 'm') {
        // Comando de Motor (-255 a 255)
        // Valores positivos = adelante, negativos = reversa, 0 = detenido
        value = constrain(value, -255, 255);
        controlMotor(value);
        Serial.print("ACK: Motor ajustado a velocidad ");
        Serial.println(value);
      }
      else {
        // Comando no reconocido
        Serial.print("ERR: Comando desconocido: ");
        Serial.println(inputString);
      }
    }
    
    // Limpiar búfer y restablecer bandera para la siguiente lectura
    inputString = "";
    stringComplete = false;
  }
}

/**
 * Función encargada del control físico del puente H L298N
 * speed: valor entero entre -255 y 255
 */
void controlMotor(int speed) {
  if (speed == 0) {
    // Parada suave (sin alimentación en el motor)
    digitalWrite(IN1_PIN, LOW);
    digitalWrite(IN2_PIN, LOW);
    analogWrite(ENA_PIN, 0);
  }
  else if (speed > 0) {
    // Giro Adelante
    digitalWrite(IN1_PIN, HIGH);
    digitalWrite(IN2_PIN, LOW);
    analogWrite(ENA_PIN, speed); // Enviar velocidad PWM al pin ENA
  }
  else {
    // Giro Reversa (atrás)
    digitalWrite(IN1_PIN, LOW);
    digitalWrite(IN2_PIN, HIGH);
    analogWrite(ENA_PIN, -speed); // Invertir el signo de la velocidad para el PWM (0-255)
  }
}

/**
 * Evento del puerto serial que lee caracteres de forma automática entre ciclos del loop.
 * Este evento es nativo de la mayoría de placas Arduino (por ejemplo, Uno/Mega/Nano).
 */
void serialEvent() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    // Si detectamos un fin de línea, marcamos que el comando está completo
    if (inChar == '\n') {
      stringComplete = true;
    } else {
      // Si no, agregamos el caracter al buffer del comando
      inputString += inChar;
    }
  }
}
