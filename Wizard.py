import matplotlib.pyplot as plt
import numpy as np

# a = [0]
j = [0,30,20,40,30,20,70,110,100,140,130,170,160,210,260,240]
r = [0,20,10,40,30,50,30,50,110,150,200,190,240,300,370,360]
i = [0,20,40,70,60,100,90,80,70,60,90,150,200,180,170,220]
m = [0,-10,-20,-30,0,20,40,90,120,170,150,210,260,250,310,300]

list_arrs = [j,r,i,m]
list_names = ["Jan", "Roman", "Ilmar", "Malik"]

x = np.arange(0, len(j))

avg = []
for round in range(len(list_arrs[0])):
    sum_val = 0
    for arr in list_arrs:
        sum_val += arr[round]
    avg.append(sum_val/len(list_arrs))

for i_arr, arr in enumerate(list_arrs):
    plt.plot(x, arr, marker="o", label=list_names[i_arr])
    max_i = np.argmax(arr)
    plt.plot(x[max_i],arr[max_i], 'd', color='black', markersize=10)

plt.plot(x, avg, color='grey', label = 'Durchschnitt', linestyle='--')
plt.legend(fontsize=30)
plt.axhline(0,0,1, linestyle="--", color="black")
plt.show()