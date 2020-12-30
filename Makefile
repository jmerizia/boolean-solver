CC = g++
CFLAGS = -std=c++2a -Wall -Wextra -Werror -O3
TARGET = prover

default:
	$(CC) $(CFLAGS) -o $(TARGET) $(TARGET).cpp

clean:
	$(RM) *.o $(TARGET)