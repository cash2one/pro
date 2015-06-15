#!/usr/bin/python
a=[1,2,3,4,5]
b=[]
c=[1,2,1,2,1,2,1,2]
print list(set(c))
print list(set(b).difference(set(a)))
print list(set(a).intersection(set(b)))
print a
print b

