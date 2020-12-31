CC = g++
CFLAGS = -std=c++2a -Wall -Wextra -Werror -Ofast
TARGET = prover

default:
	$(CC) $(CFLAGS) -o $(TARGET) $(TARGET).cpp

clean:
	$(RM) *.o $(TARGET)