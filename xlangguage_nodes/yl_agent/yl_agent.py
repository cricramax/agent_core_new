yl_instruction = """
你现在收到的是用户发来的基于plantuml的用例代码，请将他使用x语言的代码进行转写，X语言是一种形式化的建模语言，用例代码以actor开头，描述执行者，以end结尾。之后以system开头定义整个系统，其中的用例以usecase:开头，包含用例，然后使用correlation:定义关系，其中执行者和用例之间的关系用interact，用例之间的关系用include表示，最后使用end收尾，其示例如下：
建模示例如下：
actor:
operator;
end;
system missile_eletrical_system
usecase:
power_distribution;
spark;
radar;
correlation:
interact(operator,power_distribution);
include(power_distribution,spark);
include(power_distribution,radar);
end;
请将用户输入的plantuml代码转写成这种格式的x语言代码
"""
