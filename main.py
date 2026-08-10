"""
str
int
float
bool
bytes
tuple

list
set
dict

x = (1, 2)
y = x
x = (1,2,3)
print(x,y)

x = [1,2]
y = x
x[0] = 100
print(x,y)

x = [i for i in range(10) if i % 2 == 0]
print(x)
"""

def complicated_function(a,b,c=True,d=False):
    print(a,b,c,d)
    pass

complicated_function(*[1,2],**{"c": "hi"})

if __name__ == "__main__":
    print("run")

def add(a: int, b: int) -> int:
        if type(a) != int:
             return "invalid"
        return a + b

print(add("10",20))