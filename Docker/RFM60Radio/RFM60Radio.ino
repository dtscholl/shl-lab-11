#include <SPI.h>
#include <RH_RF69.h>

// Arduino Uno (__AVR_ATmega328P__)  // Feather 328P w/wing
#define RFM69_CS    4  //
#define RFM69_INT   3  //
#define RFM69_RST   2  // "A"
#define LED        13  // Blink upon transmit
#define RF69_FREQ 915.0
// Singleton instance of the radio driver
RH_RF69 rf69(RFM69_CS, RFM69_INT);

void setup()
{
  Serial.begin(9600);
  //while (!Serial) { delay(1); } // wait until serial console is open, remove if not tethered to computer

  pinMode(LED, OUTPUT);     
  pinMode(RFM69_RST, OUTPUT);
  digitalWrite(RFM69_RST, LOW);

  Serial.println("RFM69 RX Test!");
  Serial.println();

  // manual reset
  digitalWrite(RFM69_RST, HIGH);
  delay(10);
  digitalWrite(RFM69_RST, LOW);
  delay(10);

    if (!rf69.init()) {
    Serial.println("RFM69 radio init failed");
    while (1);
  }
  Serial.println("RFM69 radio init OK!");
  
  // Defaults after init are 434.0MHz, modulation GFSK_Rb250Fd250, +13dbM (for low power module)
  // No encryption
  if (!rf69.setFrequency(RF69_FREQ)) {
    Serial.println("setFrequency failed");
  }

  // If you are using a high power RF69 eg RFM69HW, you *must* set a Tx power with the
  // ishighpowermodule flag set like this:
  rf69.setTxPower(20, true);  // range from 14-20 for power, 2nd arg must be true for 69HCW

  // The encryption key has to be the same as the one in the server
  uint8_t key[] = { 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
                    0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08};
  rf69.setEncryptionKey(key);
}

int16_t packetnum = 0;  // packet counter, we increment per xmission
String serialCmd;

void loop() {
  // 1) Forward commands from ground to BeagleBone
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim(); // remove whitespace, including \r and \n

    if (cmd == "SAFE" || cmd == "SCIENCE" || cmd == "IDLE") {
      // forward as-is to the BeagleBone via RFM69
      const char* cstr = cmd.c_str();
      uint8_t len = cmd.length();    // no newline, just "SAFE" etc.
      rf69.send((uint8_t*)cstr, len);
      rf69.waitPacketSent();
      Serial.print("Forwarded command: ");
      Serial.println(cmd);
    }
  }
  delay(1000);

  char radiopacket[16] = "Test Package: # ";
  itoa(packetnum++, radiopacket+16, 10);
  Serial.print("Send "); Serial.println(radiopacket);
  
  // Send a message!
  rf69.send((uint8_t *)radiopacket, strlen(radiopacket));
  rf69.waitPacketSent();

  // Now wait for a reply
  uint8_t buf[RH_RF69_MAX_MESSAGE_LEN];
  uint8_t len = sizeof(buf);

  if (rf69.waitAvailableTimeout(5000))  { 
    // Should be a reply message for us now   
    if (rf69.recv(buf, &len)) {
      Serial.print("Got a reply: ");
      Serial.println((char*)buf);
      //blink LED 3 times, 50ms between blinks
      for (int i = 0; i < 3; i++)
       {
         digitalWrite(LED, HIGH); // Turn the LED on
         delay(50);               // Wait for 50 milliseconds
         digitalWrite(LED, LOW);  // Turn the LED off
         delay(50);               // Wait for 50 milliseconds
        }
    } 
    else {
      Serial.println("Receive failed");
    }
  } else {
    Serial.println("No reply, keep listening");
  }
}