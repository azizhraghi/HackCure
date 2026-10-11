#ifndef MOTION_H
#define MOTION_H

// Mouvement du patient (MPU6050)
namespace Motion {

enum Level { IMMOBILE, LEGER, AGITE };

bool begin();
void update();  // à appeler dans loop()
bool ready();
float accelX();
float accelY();
float accelZ();
float activity();  // écart à la gravité (m/s²), lissé
Level level();
const char* levelLabel();

}

#endif
