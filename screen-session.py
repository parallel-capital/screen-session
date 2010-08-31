#!/usr/bin/env python
# file: screen-session.py
# author: Artur Skonecki
# website: http://adb.cba.pl
# description: GNU Screen session saving program

'''
issues:
    - program won't recognize telnet and serial window types
'''


import subprocess,sys,os,getopt,glob,time,signal

class ScreenSession(object):
    """class storing GNU screen sessions"""
    pid=""
    basedir=""
    projectsdir=".screen-sessions"
    savedir=""
    procdir="/proc"
    maxwin=-1
    force=False
    lastlink="last"
    enable_layout = False
    restore_previous = False
    
    primer="screen-session-primer"
    
    blacklist = ["rm","shutdown"]
    
    __wins_trans = {}
    __scrollbacks=[]

    def __init__(self,pid,projectsdir,savedir):
        self.homedir=os.path.expanduser('~')
        self.projectsdir=str(projectsdir)
        self.basedir=os.path.join(self.homedir,self.projectsdir)
        self.savedir=str(savedir)
        self.pid=str(pid)

    def save(self):
        print("\n======CREATING___DIRECTORIES======")
        if not self.__setup_savedir(self.basedir,self.savedir):
            return False
        print("\n======SAVING___SCREEN___SESSION======")
        self.__save_screen()
        if self.enable_layout:
            print("\n======SAVING___LAYOUTS======")
            self.__save_layouts()
        print("\n======CLEANUP======")
        self.__scrollback_clean()
        print('session "%s" saved as "%s" in "%s"'%(self.pid,self.savedir,self.basedir))

    def load(self):
        print('session "%s" loading "%s"' % (self.pid,os.path.join(self.basedir,self.savedir)))
        print("\n======LOADING___SCREEN___SESSION======")
        self.__load_screen()
        if self.enable_layout:
            print("\n======LOADING___LAYOUTS======")
            self.__load_layouts()

    def exists(self):
        msg=subprocess.Popen('screen -S %s -Q @number' % self.pid, shell=True, stdout=subprocess.PIPE).communicate()[0]
        if msg.startswith('No screen session found'):
            return False
        else:
            return True

    def __remove_and_escape_bad_chars(self,str):
        # some characters are causing problems when setting window titles
        return str.replace('|','I').replace('\\','/')# how to properly escape "\"?

    def __load_screen(self):
        homewindow=subprocess.Popen('screen -S %s -Q @number' % self.pid, shell=True, stdout=subprocess.PIPE).communicate()[0].split(" ",1)[0]
        print ("Homewindow is " +homewindow)
        
        #check if target Screen is currently in some group and set hostgroup to it
        try:
            hostgroup = subprocess.Popen('screen -S %s -Q @group' % (self.pid) , shell=True, stdout=subprocess.PIPE).communicate()[0].split(" (",1)[1].rsplit(")",1)[0]
        except:
            hostgroup = "none"

        #create root group and put it into host group
        rootgroup="restore_"+self.savedir
        os.system('screen -S %s -X screen -t \"%s\" %s //group' % (self.pid,rootgroup,0 ) )
        os.system('screen -S %s -X group %s' % (self.pid,hostgroup) )
        
        rootwindow=subprocess.Popen('screen -S %s -Q @number' % self.pid, shell=True, stdout=subprocess.PIPE).communicate()[0].split(" ",1)[0]
        print("restoring Screen session inside window %s (%s)" %(rootwindow,rootgroup))

        print('number; time; group; type; title; processes;')
        wins=[]

        for filename in glob.glob(os.path.join(os.path.join(self.basedir,self.savedir),'win_*')):#this glob has to be sorted!!!
            f=open(filename)
            win=list(f)[0:6]
            f.close()
            win=self.__striplist(win)
            print (str(win))
            wins.append((win[0], win[1], win[2], win[3], self.__remove_and_escape_bad_chars(win[4]), win[5]))


        for win in wins:
            self.__wins_trans[win[0]]=self.__create_win(False,self.__wins_trans,self.pid,hostgroup,rootgroup,win[0], win[1], win[2], win[3], win[4], win[5])
        
        for win in wins:
            self.__order_group(self.__wins_trans[win[0]],self.pid,hostgroup,rootgroup,win[0], win[1], win[2], win[3], win[4], win[5])
        
        print ("Rootwindow is "+rootwindow)
        os.system('screen -S %s -X select %s' % (self.pid,rootwindow))
        
        # select last selected window
        if os.path.exists(os.path.join(self.basedir,self.savedir,"last_win")):
            last=os.readlink(os.path.join(self.basedir,self.savedir,"last_win"))
            (lasthead,lasttail)=os.path.split(last)
            lastid=lasttail.split("_",1)[1]
            print("Selecting last window %s [ previously %s ]"%(self.__wins_trans[lastid],lastid))
            os.system('screen -S %s -X select %s' % (self.pid,self.__wins_trans[lastid]))
        
        #subprocess.Popen('screen -S %s -Q @select %s' % (self.pid,rootwindow), shell=True, stdout=subprocess.PIPE)
        if self.restore_previous:
            print ("Returning homewindow " +homewindow)
            os.system('screen -S %s -X select %s' % (self.pid,homewindow))




    # Take a list of string objects and return the same list
    # stripped of extra whitespace.
    def __striplist(self,l):
        return([x.strip() for x in l])


    def __create_win(self,keep_numbering,wins_trans,pid,hostgroup,rootgroup,win,time,group,type,title,processes):
        if type=='basic':
            if keep_numbering:
                os.system('screen -S %s -X screen -t \"%s\" %s sh' % (pid,title,win) )
            else:
                #subprocess.Popen('screen -S %s -X screen -t \"%s\" sh' % (pid,title) , shell=True)
                print('creating: screen -S %s -X screen -t \"%s\" %s %s %s %s' % (pid,title,self.primer,self.projectsdir,os.path.join(self.savedir,"scrollback_"+win),os.path.join(self.savedir,"win_"+win)))
                os.system('screen -S %s -X screen -t \"%s\" %s %s %s %s' % (pid,title,self.primer,self.projectsdir,os.path.join(self.savedir,"scrollback_"+win),os.path.join(self.savedir,"win_"+win)) )

        elif type=='group':
            if keep_numbering:
                os.system('screen -S %s -X screen -t \"%s\" %s //group' % (pid,title,win ) )
            else:
                os.system('screen -S %s -X screen -t \"%s\" //group' % (pid,title) )
        else:
            print 'Unkown window type. Ignoring.'
            return -1
       

        if keep_numbering:
            newwin = win
        else:
            newwin = subprocess.Popen('screen -S %s -Q @number' % (pid) , shell=True, stdout=subprocess.PIPE).communicate()[0].split(" ",1)[0]

        return newwin
    
    def __order_group(self,newwin,pid,hostgroup,rootgroup,win,time,group,type,title,processes):
        if group=="none":
            os.system('screen -S %s -X at %s group %s' % (pid,newwin,rootgroup) )
        else:    
            os.system('screen -S %s -X at %s group %s' % (pid,newwin,group) )
            
    def __scrollback_clean(self):
        #clean up scrollback files from empty lines in the beginning of file
        for f in self.__scrollbacks:
            try:
                ftmp=f+"_tmp"
                temp=open(ftmp,'w')
                thefile = open(f,'r')
                beginning=True
                for line in thefile:
                    if beginning: 
                        if cmp(line,'\n') == 0:
                            line = line.replace('\n','')
                        else:
                            beginning=False
                    temp.write(line)
                temp.close()
                thefile.close()
                os.remove(f)
                os.rename(ftmp,f)
            except:
                print ('Unable to clean scrollback file: '+f)


    def __save_screen(self):
        homewindow=subprocess.Popen('screen -S %s -Q @number' % self.pid, shell=True, stdout=subprocess.PIPE).communicate()[0].split(" ",1)[0]
        print "Homewindow is " + homewindow

        cwin=-1
        ctty=None
        cppids={}
        searching=False
        for i in range(0,self.maxwin+1):
            os.system('screen -S %s -X select %d' % (self.pid, i) )
            if not searching:
                print('--')
            ctitle = subprocess.Popen('screen -S %s -Q @title' % (self.pid) , shell=True, stdout=subprocess.PIPE).communicate()[0]
            prev_cwin=cwin
            cwin=subprocess.Popen('screen -S %s -Q @number' % (self.pid) , shell=True, stdout=subprocess.PIPE).communicate()[0].split(" ",1)[0]
            if (cwin==prev_cwin):
                #no such window
                if searching:
                    sys.stdout.write('.')
                    sys.stdout.flush()
                else: 
                    sys.stdout.write('\nSearching for windows (set --maxwin)...')
                    searching=True
            else:
                if(searching):
                    searching=False
                    print('\n--')

                ctty = subprocess.Popen('screen -S %s -Q @tty' % (self.pid) , shell=True, stdout=subprocess.PIPE).communicate()[0]
                if(ctty=="telnet"):
                    ctype="group"
                    cpids = None
                    cpids_data=None
                else:
                    ctype="basic"
                    cpids=subprocess.Popen('lsof -F p %s' % (ctty) , shell=True, stdout=subprocess.PIPE).communicate()[0].strip().split('\n')
                    cpids_data=[]
                    for i,pid in enumerate(cpids):
                        pid=pid[1:]
                        ppid=subprocess.Popen('ps -p %s -o ppid' % (pid) , shell=True, stdout=subprocess.PIPE).communicate()[0].strip().split('\n')[1].strip()
                        cppids[pid]=ppid
                        pidinfo=self.__get_pid_info(pid)
                        cpids[i]=pid

                        cpids_data.append(pidinfo)


                try:
                    cgroup = subprocess.Popen('screen -S %s -Q @group' % (self.pid) , shell=True, stdout=subprocess.PIPE).communicate()[0].split(" (",1)[1].rsplit(")",1)[0]
                except:
                    cgroup = "none"
                
                ctime=subprocess.Popen('screen -S %s -Q @time' % (self.pid) , shell=True, stdout=subprocess.PIPE).communicate()[0]
                
                #save scrollback
                scrollback_filename=os.path.join(self.basedir,self.savedir,"scrollback_"+cwin)
                os.system('screen -S %s -X hardcopy -h %s' % (self.pid, scrollback_filename) )
                self.__scrollbacks.append(scrollback_filename)

                # sort window processes by parent pid
                # what if more than one process has no recognized ppid?
                if cpids:
                    pids_data_sort=[]
                    pids_data_sort_index=0
                    pid_tail=-1
                    pid_tail_c=-1
                    cpids_sort=[]
                    for i,pid in enumerate(cpids):
                        if cppids[pid] not in cppids.keys():
                            pids_data_sort.append(cpids_data[i])
                            cpids_sort.append(pid)
                            pid_tail=pid
                            break;
                    
                    for j in range(len(cpids)):
                        for i,pid in enumerate(cpids):
                            if pid_tail==cppids[pid]:
                                pid_tail=pid
                                pids_data_sort.append(cpids_data[i])
                                cpids_sort.append(pid)
                                break;
                    cpids_data=pids_data_sort
                    cpids=cpids_sort
               

                print('window = '+cwin+ '; saved on '+ctime+\
                        '\ntty = '+ctty  +';  group = '+cgroup+';  type = '+ctype+';  pids = '+str(cpids)+';  title = '+ctitle)
                if(cpids):
                    for i,pid in enumerate(cpids):
                        if(cpids_data[i][3]):
                            text="BLACKLISTED"
                        else: 
                            text=""
                        if self.primer in cpids_data[i][2]:
                            # clean zsh -c 'primer..' by removing '-c' 'primer..'
                            l=cpids_data[i][2].split('\0')
                            if l[1]=='-c' and l[2].startswith(self.primer):
                                # print('REMOVE THIS ARG')
                                s=str(l[0])+'\0'
                                for j in range(3,len(l)):
                                    s+=str(l[j])+'\0'
                                newdata=(cpids_data[i][0],cpids_data[i][1],s)
                                cpids_data[i]=newdata
                        print('%s    pid = %s:     cwd = %s;  exe = %s;  cmdline = %s' % (text,pid, cpids_data[i][0], cpids_data[i][1], cpids_data[i][2]))
                
                self.__save_win(cwin,ctime,cgroup,ctype,ctitle,cpids_data)

                
        self.__linkify(os.path.join(self.basedir,self.savedir),"win_"+homewindow,"last_win")
        print('\n--')

        print ("Returning homewindow = " +homewindow)
        os.system('screen -S %s -Q @select %s' % (self.pid,homewindow))

    def __load_layouts(self):
        homelayout=subprocess.Popen('screen -S %s -Q @layout number' % self.pid, shell=True, stdout=subprocess.PIPE).communicate()[0]
        if not homelayout.startswith('This is layout'):
            print("No homelayout")
            homelayout="-1"
        else:
            homelayout=homelayout.split(" ")[3]
        layout_trans={}
        for filename in glob.glob(os.path.join(self.basedir,self.savedir,'layout_*')):
            layoutname=filename.split('_',2)[2]
            layoutnumber=filename.split('_',2)[1]
            msg=subprocess.Popen('screen -S %s -Q @layout new %s' % (self.pid,layoutname), shell=True, stdout=subprocess.PIPE).communicate()[0]
            if msg.startswith('No more layout'):
                print('Maximum number of layouts reached. Ignoring layout %s (%s)'%(layoutnumber,layoutname))
            else:
                currentlayout=subprocess.Popen('screen -S %s -Q @layout number' % self.pid, shell=True, stdout=subprocess.PIPE).communicate()[0]
                currentlayout,currentlayoutname = currentlayout.split('layout',1)[1].rsplit('(')
                currentlayout = currentlayout.strip()
                currentlayoutname = layoutname.rsplit(')')[0]
                
                layout_trans[layoutnumber]=currentlayout

                print("session %s sourcing %s"%(self.pid,filename))
                os.system('screen -S %s -X source \"%s\"' % (self.pid, filename) )
                (head,tail)=os.path.split(filename)
                
                filename2=os.path.join(head,"win"+tail)
                f=open(filename2,'r')
                focus_offset=int(f.readline().split(" ")[1])
                for line in f:
                    line=line.strip()
                    if not line=="-1":
                        os.system('screen -S %s -Q @select %s' % (self.pid,self.__wins_trans[line]))
                    os.system('screen -S %s -X focus' % (self.pid) )
                f.close()
                
                # restore focus on the right region
                os.system('screen -S %s -X focus top' % (self.pid) )
                for i in range(0,focus_offset):
                    os.system('screen -S %s -X focus' % (self.pid) )
        
        # select last layout
        if os.path.exists(os.path.join(self.basedir,self.savedir,"last_layout")) and len(layout_trans)>0:
            last=os.readlink(os.path.join(self.basedir,self.savedir,"last_layout"))
            (lasthead,lasttail)=os.path.split(last)
            last=lasttail.split("_",2)
            lastname=last[2]
            lastid=last[1]
            print("Selecting last layout %s (%s) [ previously %s ]"%(layout_trans[lastid],lastname,lastid))
            os.system('screen -S %s -Q @layout select %s' % (self.pid,layout_trans[lastid]))
            # ^^ layout numbering may change, use layout_trans={} !

        if self.restore_previous:
            if homelayout!="-1":
                print("Returning homelayout %s"%homelayout)
                os.system('screen -S %s -Q @layout select %s' % (self.pid,homelayout))
            else:
                print('No homelayout - unable to return.')

    def __terminate_processes(self,ident):
        #get list of subprograms and finish them all
        procs=subprocess.Popen('ps x |grep "%s"' % (ident), shell=True, stdout=subprocess.PIPE).communicate()[0]
        procs=procs.split('\n')
        nprocs=[]
        for p in procs:
            nprocs.append(p.strip().split(' ')[0])
        procs=nprocs
        
        for p in procs:
            try:
                os.kill(int(p),signal.SIGTERM)
            except:
                pass

    __get_focus_offset_c=0
    def __get_focus_offset(self):
        focus_offset=0
        os.system('screen -S %s -X screen %s -m %d-%d'%(self.pid,self.primer,os.getpid(),self.__get_focus_offset_c))
        ident="%s -m %d-%d" %(self.primer,os.getpid(),self.__get_focus_offset_c)
        self.__get_focus_offset_c+=1
        markertty = subprocess.Popen('screen -S %s -Q @tty' % (self.pid) , shell=True, stdout=subprocess.PIPE).communicate()[0]
        os.system('screen -S %s -X focus top' % (self.pid) )

        while True:
            ctty = subprocess.Popen('screen -S %s -Q @tty' % (self.pid) , shell=True, stdout=subprocess.PIPE).communicate()[0]
            if ctty==markertty:
                break
            else:
                os.system('screen -S %s -X focus' % (self.pid) )
                focus_offset+=1
        self.__terminate_processes(ident)
        return focus_offset


    def __save_layouts(self):
        
        homelayout=subprocess.Popen('screen -S %s -Q @layout number' % self.pid, shell=True, stdout=subprocess.PIPE).communicate()[0]
        if not homelayout.startswith('This is layout'):
            print("No layouts to save. Create layouts with \":layout new\"")
            return False
        homelayout,layoutname = homelayout.split('layout',1)[1].rsplit('(')
        homelayout = homelayout.strip()
        layoutname = layoutname.rsplit(')')[0]
        homelayoutname = layoutname
        print("Homelayout is %s (%s)"% (homelayout,layoutname))
        currentlayout=homelayout
       

        loop_exit_allowed=False
        while currentlayout!=homelayout or not loop_exit_allowed:
            loop_exit_allowed=True
            print('--')
            print("layout = %s (%s)"% (currentlayout,layoutname))
            os.system('screen -S %s -X layout dump \"%s\"' % (self.pid, os.path.join(self.basedir,self.savedir,"layout_"+currentlayout+"_"+layoutname)) )
            region_c = int(subprocess.Popen('grep "split" %s | wc -l' % (os.path.join(self.basedir,self.savedir,"layout_"+currentlayout+"_"+layoutname)) , shell=True, stdout=subprocess.PIPE).communicate()[0].strip())+1
            print("regions (%d):" % region_c)
            focus_offset=self.__get_focus_offset()
            os.system('screen -S %s -X focus top' % (self.pid) )
            win=[]
            for i in range(0,region_c):
                currentnumber=subprocess.Popen('screen -S %s -Q @number' % self.pid, shell=True, stdout=subprocess.PIPE).communicate()[0].split(" ",1)[0]+'\n'
                windows = subprocess.Popen('screen -S %s -Q @windows' % (self.pid) , shell=True, stdout=subprocess.PIPE).communicate()[0]
                print('windows: '+ windows)
                offset=0
                findactive=False
                for j in range(windows.count('$')):
                    index=windows.find('$',offset)
                    if(index!=-1):
                        if windows[index-1]=='*' or windows[index-2]=='*':
                            findactive=True
                            print ('focus offset: '+str(offset))
                            break
                        else:
                            offset=index+1

                if not findactive:
                    currentnumber="-1\n"
                print("current region = %s; window number = %s"%(i,currentnumber.strip()))
                win.append(currentnumber)
                os.system('screen -S %s -X focus' % (self.pid) )

            f=open(os.path.join(self.basedir,self.savedir,"winlayout_"+currentlayout+"_"+layoutname),"w")
            f.writelines("offset %d\n"%focus_offset)
            f.writelines(win)
            f.close()
            
            #get back to originally focused window
            for i in range(0,focus_offset):
                os.system('screen -S %s -X focus' % (self.pid) )


            os.system('screen -S %s -X layout next' % (self.pid) )
            
            currentlayout=subprocess.Popen('screen -S %s -Q @layout number' % self.pid, shell=True, stdout=subprocess.PIPE).communicate()[0]
            currentlayout,layoutname = currentlayout.split('layout',1)[1].rsplit('(')
            currentlayout = currentlayout.strip()
            layoutname = layoutname.rsplit(')')[0]
        
        self.__linkify(os.path.join(self.basedir,self.savedir),"layout_"+homelayout+"_"+homelayoutname,"last_layout")
        
        print("Returned homelayout %s (%s)"% (homelayout,homelayoutname))
        
        # select last selected window
        if os.path.exists(os.path.join(self.basedir,self.savedir,"last_win")):
            last=os.readlink(os.path.join(self.basedir,self.savedir,"last_win"))
            (lasthead,lasttail)=os.path.split(last)
            lastid=lasttail.split("_",1)[1]
            print("Selecting last window %s"%(lastid))
            os.system('screen -S %s -X select %s' % (self.pid,lastid))

        return True
           
    def __linkify(self,dir,dest,targ):
        cwd=os.getcwd()
        os.chdir(dir)
        try:
            os.remove(targ)
        except:
            pass
        os.symlink(dest,targ)
        os.chdir(cwd)


    def __save_win(self,winid,time,group,type,title,pids_data):
        fname=os.path.join(self.basedir,self.savedir,"win_"+winid)
        print ("Saving window %s" % winid)
        
        pids_data_len="0"
        if(pids_data):
            pids_data_len=str(len(pids_data))
        
        basedata=(winid,time,group,type,title,pids_data_len)
        f=open(fname,"w")
        for data in basedata:
            f.write(data+'\n')

        if(pids_data):
            for pid in pids_data:
                f.write("-\n")
                for i,data in enumerate(pid):
                    if i == 2:
                        f.write(str(len(data.split('\0'))-1)+'\n')
                        f.write(str(data)+'\n')
                    else:
                        f.write(str(data)+'\n')
        f.close()




    def __get_pid_info(self,pid):
        piddir=os.path.join(self.procdir,pid)
        
        cwd=os.readlink(os.path.join(piddir,"cwd"))
        exe=os.readlink(os.path.join(piddir,"exe"))
        f=open(os.path.join(piddir,"cmdline"),"r")
        cmdline=f.read()
        f.close()
        (exehead,exetail)=os.path.split(exe)
        if exetail in self.blacklist:
            blacklist=True
        else:
            blacklist=False
        
        return (cwd,exe,cmdline,blacklist)

    def __setup_savedir(self,basedir,savedir):
        print ("Setting up session directory %s" % savedir)
        if not os.path.exists(basedir):
            os.makedirs(basedir)

        if os.path.exists(os.path.join(basedir,savedir)):
            print("Directory \"%s\" in \"%s\" already exists. Use --force to overwrite." % (savedir, basedir))
            if self.force:
                print('forcing..')
                print('cleaning up \"%s\"' % savedir)
                for filename in glob.glob(os.path.join(basedir,savedir,'win_*')):
                    os.remove(filename)
                for filename in glob.glob(os.path.join(basedir,savedir,'scrollback_*')):
                    os.remove(filename)
                for filename in glob.glob(os.path.join(basedir,savedir,'layout_*')):
                    os.remove(filename)
                for filename in glob.glob(os.path.join(basedir,savedir,'winlayout_*')):
                    os.remove(filename)
                self.__linkify(basedir,savedir,self.lastlink)
                return True
            else:
                print('Aborting.')
                return False
        else:
            os.makedirs(os.path.join(basedir,savedir))
            self.__linkify(basedir,savedir,self.lastlink)
            return True



def doexit(var=0,waitfor=True):
    if waitfor:
        raw_input('Press any key to exit...')
    sys.exit(var)

def usage():
    print('Usage:\n\
  -l --load                            - loading mode\n\
  -s --save                            - saving mode\n\
  -i --in     <session or directory>   - input\n\
  -o --out    <session or directory>   - output\n\
  -m --maxwin <number>                 - biggest window number\n\
  -f --force  <number>                 - force saving\n\
  -r --restore                         - restore windows after loading\n\
  -y --no-layout                          - disable layout saving/loading\n\
  -d --dir                             - directory holding saved sessions\n\
                                         (default: $HOME/.screen-sessions)\n\
  -h --help                            - show this message\n\
  \n\
Examples:\n\
$ screen-session --save --maxwin 20 --in PID --out mysavedsession\n\
$ screen-session --load --in mysavedsession --out PID\n\
\n')

if __name__=='__main__':
    
    if len(sys.argv)>1:
        if sys.argv[1]=='--wait':
            waitfor=True
        else:
            waitfor=False
    else:
        waitfor = False

    try :
        opts,args = getopt.getopt(sys.argv[1:], "ryi:c:wfi:o:m:lsd:hv", ["restore","no-layout","current-session=","wait","force","in=", "out=","maxwin=","load","save","dir=","help"])
    except getopt.GetoptError, err:
        print('Bad options.')
        usage()
        doexit(2,waitfor)
    
    current_session=None
    restore = False
    verbose = False
    force = False
    enable_layout = True
    mode = 0
    projectsdir =None
    savedir = None
    maxwin = -1
    input=None
    output=None
    for o, a in opts:
        if o == "-v":
            verbose = True
        elif o in ("-c","--current-session"):
            current_session = a
        elif o in ("-r","--restore"):
            restore = True
        elif o in ("-f","--force"):
            force = True
        elif o in ("-y","--no-layout"):
            enable_layout = False
        elif o in ("-h","--help"):
            usage()
            doexit(0,waitfor)
        elif o in ("-w","--wait"):
            waitfor = True
        elif o in ("-m","--maxwin"):
            maxwin = int(a)
        elif o in ("-s","--save"):
            mode = 1
        elif o in ("-l","--load"):
            mode = 2
        elif o in ("-d","--dir"):
            projectsdir = a
        elif o in ("-i","--in"):
            input = a
        elif o in ("-o","--out"):
            output = a
        else:
            doexit("Unhandled option",waitfor)


    if not projectsdir:
        sys.stdout.write("projects directory: ")
        directory = '.screen-sessions'
        print('$HOME/'+directory)
        projectsdir = directory

    if mode==0:
        usage()
        doexit(0,waitfor)
    elif mode==1:
        if not input:
            if current_session:
                input = current_session
            else:
                print("for saving you must specify target Screen session PID as --in")
                doexit("Aborting",waitfor)
        pid = input
        if not output:
            savedir = pid
        else:
            savedir = output
    elif mode == 2:
        if not input:
            input="last"
            try:
                input=os.readlink(os.path.join(projectsdir,input))
            except:
                print("No recent session to load")
                doexit("Aborting",waitfor)
        if not output:
            if current_session:
                output = current_session
            else:
                print("for loading you must specify target Screen session PID as --out")
                doexit("Aborting",waitfor)
        pid = output
        savedir = input
    
    
    scs=ScreenSession(pid,projectsdir,savedir)
    if not scs.exists():
        print('No such session: %s'%pid)
        doexit(1,waitfor)
        
    if savedir == scs.lastlink and mode==1:
        print("savedir cannot be named \"%s\". Aborting." % savedir)
        doexit(1,waitfor)
    
    if (maxwin==-1) and (mode==1):
        print("for saving specify --maxwin (biggest window number in session)")
        maxwin=int(subprocess.Popen('screen -S %s -Q @maxwin' % scs.pid, shell=True, stdout=subprocess.PIPE).communicate()[0].split(':')[1].strip())

    scs.maxwin = maxwin
    scs.force = force
    scs.enable_layout=enable_layout
    scs.restore_previous = restore
    if mode==1:
        scs.save()
        os.system('screen -S %s -X echo "screen-session finished saving"'%input)
    elif mode==2:
        scs.load()
        os.system('screen -S %s -X echo "screen-session finished loading"'%input)
    else:
        print('No mode specified --load or --save')

    doexit(0,waitfor)


