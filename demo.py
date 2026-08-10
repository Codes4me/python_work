name = "Nathan"
age = 18
height = 5.0
is_learning = True

print(name + " is " + str(age))
message = f"Hi, my name is {name}."
print(message)
#user_name = input("What is your age? ")
#print(int(user_name) + 1)
if age >= 65:
    print("You are a senior")
elif age >= 18:
    print("You are an adult.")
else:
    print("You are a minor.")

groceries = ["apple", "milk", "butter"]
for number in range(5):
    print(number)

def greet(name):
    print(f"Hello, {name}!")
greet("Tim")

def calculate_tip(bill,percent):
    tip = bill * (percent / 100)
    return tip

bill_amount = float(input("What was your bill? "))
tip_percent = float(input("What percent do you want to tip?"))

tip = calculate_tip(bill_amount, tip_percent)
total = bill_amount + tip

print(f"Tip amount: ${tip}")
print(f"Total to pay: ${total}")