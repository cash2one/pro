import datetime   
import time
  
def main():  
    d = '20140607'
    a=time.strptime(d,'%Y%m%d');
    print a
    begin=date.date(*a[:3])
    print begin
    end = datetime.date(2014,6,7)  
    print begin
    print end
    for i in range((end - begin).days+1):  
        day = begin + datetime.timedelta(days=i)  
        print str(day)  
   
if __name__ == '__main__':  
    main() 
