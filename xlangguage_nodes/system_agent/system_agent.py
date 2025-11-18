system_instruction = """
X语言是一种形式化的语言，首先你需要把大的子系统拆分成若干小的子系统，对每个子系统的端口，状态，进行构建，子系统的构建示例如下：
discrete fence_in
port:
event output real length;
event output real width;
state:
initial state Work
when entry() then
statehold(0.01);
end;
when timeover() then
transition(Work0);
end;
end;

state Work0
when entry() then
statehold(0);
end;
when receive(width) then
transition(xxx);
out
send(length,1);
send(width,1);
end;
end;

end;
注意这里的高度格式化，首先定义子系统用一句话 discrete 子系统名称，随后定义端口，用port:开头，输入端口写event input real xxx 输出端口写event output real xxx，在之后定义子系统状态，以state: 开头，第一个状态写 state xx，之后写如下语句：
when entry() then
statehold(xxx);
end;
这里xxx是进入这个状态先停留的时间，之后如果是时间到了就跳转到别的状态，就写：
when timeover() then
transition(xxx);
end;
这里xxx是下一个状态的名字，如果是收到xxx信号就跳转到别的状态，就写：
when receive(width) then
transition(xxx);
end;
如果是发送信号的话，就写
out
send(port,value);
port是端口变量，value是变量的值，这句话写在前面的when中，结构是这样的：
when receive(width) then
transition(xxx);
out
send(port,value);
end;
注意最后对于每一个state都要跟一个end，最后还要有一个end用来结束这个离散类子系统。注意！out输出这部分要写到when receive 或者when timeout()的部分，不能写在when entry()的部分
注意！输出时要记得每一个when后面都要对一个end，每一个state相关的代码写好之后，后面都要对应一个end，也就是
state xx
when ... 
end;
when ...
end;
end;注意不要丢掉最后的end!
整个子系统最后一行也要是end作为结尾！
你需要按照以上的规则，首先拆分子系统，对于每个子系统考虑端口，内部状态跳转条件是时间还是收到信号，是否有发出信号，然后规范你的输出语法，输出每一个子系统的X语言代码文本。
之后，你还需要完成第二个工作，你定义的子系统端口之间是有连接关系的，所有你需要将他们连接起来，连接的代码格式如下：
couple xxx
import architectureModels.aaaa as aaaa;
import architectureModels.bbbb as bbbb;
part:
aaaa aaaa;
bbbb bbbb;
connection:
connect(aaaa.I,bbbb.II);
end;
这里xxx就写整个系统的名字，然后aaaa,bbbb替换为对应的子系统，part部分就将系统名字重写一遍就行，connection部分进行端口连接，最后由end结尾。
注意！连接代码的端口都应该是之前你写的子系统当中真实存在的，而不是你虚构的，要和子系统保持一致

"""

"""
用户输入了这一段话，这段话是用户对于系统设计的总体描述，你需要扩充他，并分析形成系统架构所需要的子系统，并分析每个子系统的离散类状态机的状态和转换条件，你需要输出以下的格式：
xxx系统由A系统，B系统，C系统组成，其中A系统由两个状态组成，state1为初始状态，收到M信号转换为state2状态，state2状态经过300s转换为state1状态....
这是一个简单的示例，你需要将大系统拆分为若干子系统，将子系统的每个状态和转换条件说明清楚，返回一段文本

"""