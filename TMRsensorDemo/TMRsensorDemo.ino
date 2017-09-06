/*
TMR Angle Sensor example code

This code demonstrates how to read data from ADS1015 ADC on the TMR Sensor demonstration board.

You would need to install Adafruit_ADS1X15 library
v1.2.1 by soligen2010
https://github.com/soligen2010/Adafruit_ADS1X15

Other libraries used:
https://github.com/adafruit/Adafruit-GFX-Library
https://github.com/adafruit/Adafruit_SSD1306
https://github.com/adafruit/Adafruit_NeoPixel

This example uses an OLED dispaly and a neopixel to show data.
Display: 128X64 0.96 inch OLED Display such as
https://www.aliexpress.com/store/product/1Pcs-blue-128X64-OLED-LCD-LED-Display-Module-0-96-I2C-IIC-SPI-Serial-new-original/535576_32523645959.html

Author: Shunya Sato

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
*/

#include <Wire.h>
#include <math.h>
#include <Adafruit_ADS1015.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Adafruit_NeoPixel.h>

Adafruit_ADS1115 ads;  /* Use this for the 16-bit version */
//Adafruit_ADS1015 ads;     /* Use this for the 12-bit version */

// cheap OLED display
#define OLED_RESET -1
Adafruit_SSD1306 display(OLED_RESET);

#define PIN 2 // Neopixel pin
Adafruit_NeoPixel strip = Adafruit_NeoPixel(1, PIN, NEO_GRB + NEO_KHZ800);

float multiplier; // convert ADC reading to mV
const double rad2deg_multiplier = 180 / M_PI;
float rho_max = 1200; // initial maximum of sqrt(sq(sin_mv) + sq(cos_mv))

void setup(void)
{
  Serial.begin(115200);
  Serial.println("Hello!");

  Serial.println("Getting differential reading from AIN0 (P) and AIN1 (N)");
  Serial.println("ADC Range: +/- 6.144V (1 bit = 3mV/ADS1015, 0.1875mV/ADS1115)");

  // The ADC input range (or gain) can be changed via the following
  // functions, but be careful never to exceed VDD +0.3V max, or to
  // exceed the upper and lower limits if you adjust the input range!
  // Setting these values incorrectly may destroy your ADC!
  //                                                                ADS1015  ADS1115
  //                                                                -------  -------
  ads.setGain(GAIN_TWOTHIRDS);  // 2/3x gain +/- 6.144V  1 bit = 3mV      0.1875mV (default)
  // ads.setGain(GAIN_ONE);        // 1x gain   +/- 4.096V  1 bit = 2mV      0.125mV
  // ads.setGain(GAIN_TWO);        // 2x gain   +/- 2.048V  1 bit = 1mV      0.0625mV
  // ads.setGain(GAIN_FOUR);       // 4x gain   +/- 1.024V  1 bit = 0.5mV    0.03125mV
  // ads.setGain(GAIN_EIGHT);      // 8x gain   +/- 0.512V  1 bit = 0.25mV   0.015625mV
  // ads.setGain(GAIN_SIXTEEN);    // 16x gain  +/- 0.256V  1 bit = 0.125mV  0.0078125mV

  ads.begin();

  multiplier = ads.voltsPerBit()*1000.0F;    /* Sets the millivolts per bit */

  /* Use this to set data rate for the 12-bit version (optional)*/
  //ads.setSPS(ADS1015_DR_3300SPS);      // for ADS1015 fastest samples per second is 3300 (default is 1600)

  /* Use this to set data rate for the 16-bit version (optional)*/
  ads.setSPS(ADS1115_DR_860SPS);      // for ADS1115 fastest samples per second is 860 (default is 128)

  display.begin(SSD1306_SWITCHCAPVCC, 0x3C);  // initialize with the I2C addr 0x3D (for the 128x64)
  display.clearDisplay();
  display.setTextSize(2);
  display.setTextColor(WHITE);
  display.setCursor(0,0);
  display.println("TMR Sensor");
  display.display();

  strip.begin();
  strip.show(); // Initialize all pixels to 'off'

}

void loop(void)
{
  int16_t results0_1, results2_3;
  results0_1 = ads.readADC_Differential_0_1();
  results2_3 = ads.readADC_Differential_2_3();
  float sin_mv = results0_1 * multiplier;
  float cos_mv = results2_3 * multiplier;

  // Note that this is a simple way to derive angle with limited accuracy
  // TDK has developed elavorated correction algorithm to achieve higher accuracy.
  // Please contact TDK for details.
  double angle_rad = atan2(sin_mv, cos_mv);
  double angle = angle_rad * rad2deg_multiplier; // convert radian to degree
  float rho = sqrt(sq(sin_mv)+sq(cos_mv));
  if (rho > rho_max) rho_max = rho;
  float rho_ratio = rho / rho_max;

  Serial.print(sin_mv);
  Serial.print(",");
  Serial.print(cos_mv);
  Serial.print(",");
  Serial.println(angle);

  updateDisplay(angle, angle_rad, rho_ratio);
  updateNeopixel(angle);

  delay(100);
}

void updateDisplay(double angle, double angle_rad, float rho_ratio){
  // OLED display of size: 128x64
  display.clearDisplay();
  display.setTextSize(2);
  display.setTextColor(WHITE);
  display.setCursor(0,0);
  display.println("TMR Sensor");
  display.setCursor(0,20);
  display.println("Angle: ");
  display.setCursor(0,40);
  display.println(angle);

  // draw compass
  int r = 20;
  // draw outter circle
  display.drawCircle(128-r-1, 64-r-1, r, WHITE);
  // draw angle line
  display.drawLine(128-r-1, 64-r-1, 128-r-1+r*cos(angle_rad), 64-r-1-r*sin(angle_rad), WHITE);
  // draw Lissajous
  display.drawCircle(128-r-1+r*rho_ratio*cos(angle_rad), 64-r-1-r*rho_ratio*sin(angle_rad), 3, WHITE);
  display.display();
}

void updateNeopixel(double angle){
  int pos = map(angle, -180, 180, 0, 255);
  pos = constrain(pos, 0, 255);
  strip.setPixelColor(0, Wheel(pos));
  strip.show();
}

// Input a value 0 to 255 to get a color value.
// The colours are a transition r - g - b - back to r.
uint32_t Wheel(byte WheelPos) {
  WheelPos = 255 - WheelPos;
  if(WheelPos < 85) {
   return strip.Color(255 - WheelPos * 3, 0, WheelPos * 3);
  } else if(WheelPos < 170) {
    WheelPos -= 85;
   return strip.Color(0, WheelPos * 3, 255 - WheelPos * 3);
  } else {
   WheelPos -= 170;
   return strip.Color(WheelPos * 3, 255 - WheelPos * 3, 0);
  }
}
