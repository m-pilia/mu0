; This program computes the quotient and remainder in the Euclidean division
; of two integer numbers. The division is implemented subtracting the divisor
; from the dividend, stopping a step until the difference becomes negative,
; and counting the number of iterations.

; Load initial values to memory
INI 0x100 0xfa3 ; dividend: 4003
INI 0x101 0x52  ; divisor:  82
INI 0x102 0x1   ; unit
INI 0x103 0x0   ; remainder
INI 0x104 0x0   ; quotient

; Actual program code
LOAD  0x100 ; load dividend
STORE 0x103 ; save it as temporary remainder
LOAD  0x103 ; load temporary reminder
SUB   0x101 ; subtract divisor to the temporary remainder
JGE   0x6   ; if result is >= 0, the algorithm has not finished yet
STOP
STORE 0x103 ; store new temporary remainder
LOAD  0x104 ; increment quotient
ADD   0x102
STORE 0x104
JUMP  0x2
