'''
#test
#first pull request
# second commit  mhello
import random

user_0 = {
    'username': 'efermi',
    'first': 'enrico',
    'last': 'fermi',
    'firsts': 'enrico',
    'affragado': "enrico",
}
user_0.setdefault("info",()).append("none")
seen_values = set()

for key, value in user_0.items():
    # Only execute when the value is completely new
    if value not in seen_values:
        seen_values.add(value)

        print(f"Key: {key}")    
        print(f"Value: {value}")


for key, value in user_0.items():
    print(f"\nKey: {key}")
    print(f"Value: {value}")

print("")

for key in user_0.keys():
    
    print(f"{key.title()}")

    
numbers = [1,2,3,4,5]
for num in numbers:
    if num == 5:
        print("Found 5!")
        break
else:
    print("5 was not found.")

nested = [[1,2],[3,4],[5,6]]
flattened = [item for sublist in nested for item in sublist]
print(flattened)

a_tuple = (10,20,30)
x,_,z = a_tuple
print(x,z)
a=1
b=2
a,b=b,a
print(a,b)

def add(a,b):
    print(f'adding: {a} + {b}')
    return a + b
print(add(10,15))

a = 1
b = 1
print(a < b)
print(a==b)
print(a!=b)

a,b = 10, 'fifteen'
try:
    print(a + b)
except TypeError as e:
    print(f'Enter a integer or flaot')
except Exception as e:
    print('Something went wrong: {e}')


from math import sqrt,tan,pi
print(tan(pi/2))

bomb = ['Bang','Boom','Bam','Pow','Poof','Pah']

while True:
    user_input = input('You: ').lower()

    if user_input in ['hi', 'hello']:
        print('Bot: Hello!')
    elif user_input == 'how are you?':
        print('Bot: Good, how about you?')
    elif user_input in ['+', 'add']:
        print('Let\'s do some addition! Please enter two numbers.')
        try:
            num1 = float(input('First number: '))
            num2 = float(input('Second number: '))
            print(f'The sum is {num1 + num2}')
        except ValueError:
            print(f'That doesn\'t seem like a valid number.')
        except Exception as e:
            print(f'{e}')
    elif user_input in ['bomb','explode','dynamite','tnt','explosion']:
        print(random.choice(bomb))
    else:
        print('Bot doesnt understand.')
'''