import sys
import types
import textwrap

class MenuSystem():
    def __init__(self):
        self.menus = {}
        self.width = 80
    
    def run(self, mainMenu):
        nextMenu = mainMenu
        prevMenu = None
        while nextMenu != None:
            currentMenu = self.menus[nextMenu]
            nextMenu = currentMenu.show(prevMenu)
            if type(nextMenu) == types.ListType:
                for next in nextMenu:
                    self.run(next)
                nextMenu = None
            prevMenu = currentMenu
    
    def setAttr(self, attrName, value=None):
        if not hasattr(self, attrName):
            setattr(self, attrName, value)

class Menu():
    system = MenuSystem()
    
    def getDefaultOption(self, name):
        if name == "SPACE":
            return Option(None, None)
    
    def __init__(self, title, text, options, initializer=None):
        assert title not in Menu.system.menus
        Menu.system.menus[title] = self
        
        self.title = title
        self.text = text
        self.options = options
        self.optDict = {}
        for i in range(len(options)):
            option = options[i]
            # Replace string with the default option it refers to
            if type(option) in types.StringTypes:
                option = self.getDefaultOption(option)
                options[i] = option
            # Options must have a defined key
            if option.key != None:
                option.menu = self
                assert option.key not in self.optDict
                self.optDict[option.key] = option
                if option.dataInput != None:
                    self.setAttr(option.dataInput)
        self.initializer = initializer
        self.doAlignText = True
    
    def setDefault(self, key):
        for option in self.options:
            option.isDefault = False
        self.optDict[key].isDefault = True
    
    def getAttrString(self, attrName):
        if not hasattr(self, attrName) or getattr(self, attrName) == None:
            return ""
        else:
            return getattr(self, attrName)
    
    def setAttr(self, attrName, value=None):
        if not hasattr(self, attrName):
            setattr(self, attrName, value)
    
    def printText(self):
        if self.doAlignText:
            print >> sys.stderr, self.alignText(self.text)
        else:
            print >> sys.stderr, self.text

    def printBorder(self, title=None, style="="):
        if title != None:
            border = ((self.system.width - len(title) - 2) / 2) * style
            titleBar = border + " " + title + " " + border
            titleBar += (len(titleBar) - self.system.width) * style
            print >> sys.stderr, titleBar
        else:
            print >> sys.stderr, self.system.width * style
    
    def printOptions(self):
        for option in self.options:
            option.show()
    
    def getDataInput(self, attr, value=None, check=None):
        self.printBorder("Set attribute", "-")
        if value == None:
            value = getattr(self, attr, "")
        print >> sys.stderr, "Current value:", value
        ok = False
        while not ok:
            print >> sys.stderr, ">",
            value = raw_input()
            if check != None:
                ok = check(value)
                if not ok:
                    print "Illegal input value"
            else:
                ok = True
        self.printBorder(style="-")
        return value

    def getChoice(self, items):
        choice = None
        default = None
        for item in items:
            if item.isDefault:
                default = item
                break
        while choice == None:
            print >> sys.stderr, ">",
            choice = raw_input()
            #print "Choice", type(choice), len(choice), "End"
            if choice.strip() == "" and default != None:
                choice = default.key
            if choice.lower() in self.optDict.keys():
                choiceLower = choice.lower()
                opt = self.optDict[choiceLower]
                if opt.toggle != None:
                    opt.toggle = not opt.toggle
                    return self.title
                elif opt.dataInput != None:
                    setattr(self, opt.dataInput, self.getDataInput(opt.dataInput))
                    return self.title
                else:
                    opt.do()
                    print >> sys.stderr, "\n\n"
                    return opt.nextMenu
            else:
                print >> sys.stderr, "Unknown option", choice
                choice == None
    
    def alignText(self, text):
        lines = text.split("\n")
        paragraphs = [""]
        for line in lines:
            if line.strip() == "":
                paragraphs.append("")
            else:
                paragraphs[-1] += line.strip() + " "
        paragraphsToKeep = []
        for paragraph in paragraphs:
            paragraph = "\n".join(textwrap.wrap(paragraph, width=self.system.width))
            if paragraph.strip() != "":
                paragraphsToKeep.append(paragraph)
        return "\n\n".join(paragraphsToKeep)
                
    def show(self, prevMenu):
        #if prevMenu != None:
        #    print >> sys.stderr, "Menu", self.title, "prev", prevMenu.title
        if self.initializer != None:
            self.initializer(self, prevMenu)
        self.printBorder(self.title)
        self.printText()
        self.printBorder(style="-")
        assert self.options != None and len(self.options) >= 1
        self.printOptions()
        self.printBorder()
        return self.getChoice(self.options)

class Option:
    SPACE = "SPACE"
    QUIT = "QUIT"
    
    def __init__(self, key, text, nextMenu=None, handler=None, isDefault=False, toggle=None, dataInput=None):
        self.key = key
        self.text = text
        self.toggle = toggle
        self.dataInput = dataInput
        self.isDefault = isDefault
        self.menu = None
        self.handler = handler
        self.handlerArgs = []
        self.nextMenu = nextMenu
    
    def show(self, alignText=True):
        if self.key == None: # SPACE
            print >> sys.stderr
            return
        
        if self.isDefault:
            print >> sys.stderr, " * ",
        elif self.toggle != None:
            if self.toggle:
                print >> sys.stderr, "[X]",
            else:
                print >> sys.stderr, "[ ]",
        else:
            print >> sys.stderr, "   ",
        print >> sys.stderr, self.key + ")",
        
        if self.dataInput != None:
            print >> sys.stderr, self.text, "(" + self.menu.getAttrString(self.dataInput) + ")"
        else:
            print >> sys.stderr, self.text
    
    def do(self):
        if self.handler == None:
            return
        elif type(self.handler) == types.ListType:
            for i in range(len(self.handler)):
                if len(self.handlerArgs) > i:
                    self.handler[i](*self.handlerArgs[i])
                else:
                    self.handler[i]()
        else:
            self.handler(*self.handlerArgs)
    
#    def do(self):
#        assert self.action != None
#        if self.action.__class__.__name__ == Menu.__name__:
#            return self.action
#        else:
#            self.action(**self.actionArgs)
#            return None

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    
    m = Menu("Main menu", 
             "Some Text."
             [Option("Y", "Yes", None, True), Option("N", "No")])
    m.show()
