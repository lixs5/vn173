# encoding: UTF-8

"""
一个多信号组合策略，基于的信号包括：
RSI（1分钟）：大于70为多头、低于30为空头
CCI（1分钟）：大于10为多头、低于-10为空头
MA（5分钟）：快速大于慢速为多头、低于慢速为空头
"""

from vnpy.trader.vtObject import VtBarData
from vnpy.trader.vtConstant import EMPTY_STRING
from vnpy.trader.app.ctaStrategy.ctaTemplate import (TargetPosTemplate, 
                                                     CtaSignal,
                                                     BarGenerator, 
                                                     ArrayManager)


########################################################################
class RsiSignal(CtaSignal):
    """RSI信号"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(RsiSignal, self).__init__()
        
        self.rsiWindow = 14
        self.rsiLevel = 20
        self.rsiLong = 50 + self.rsiLevel
        self.rsiShort = 50 - self.rsiLevel
        
        self.bg = BarGenerator(self.onBar)
        self.am = ArrayManager()
        
    #----------------------------------------------------------------------
    def onTick(self, tick):
        """Tick更新"""
        self.bg.updateTick(tick)
        
    #----------------------------------------------------------------------
    def onBar(self, bar):
        """K线更新"""
        self.am.updateBar(bar)
        
        if not self.am.inited:
            self.setSignalPos(0)
            
        rsiValue = self.am.rsi(self.rsiWindow)
        
        if rsiValue >= self.rsiLong:
            self.setSignalPos(1)
        elif rsiValue <= self.rsiShort:
            self.setSignalPos(-1)
        else:
            self.setSignalPos(0)


########################################################################
class CciSignal(CtaSignal):
    """CCI信号"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(CciSignal, self).__init__()
        
        self.cciWindow = 30
        self.cciLevel = 10
        self.cciLong = self.cciLevel
        self.cciShort = -self.cciLevel
        
        self.bg = BarGenerator(self.onBar)
        self.am = ArrayManager()        
        
    #----------------------------------------------------------------------
    def onTick(self, tick):
        """Tick更新"""
        self.bg.updateTick(tick)
        
    #----------------------------------------------------------------------
    def onBar(self, bar):
        """K线更新"""
        self.am.updateBar(bar)
        
        if not self.am.inited:
            self.setSignalPos(0)
            
        cciValue = self.am.cci(self.cciWindow)
        
        if cciValue >= self.cciLong:
            self.setSignalPos(1)
        elif cciValue<= self.cciShort:
            self.setSignalPos(-1)    
        else:
            self.setSignalPos(0)
    

########################################################################
class MaSignal(CtaSignal):
    """双均线信号"""
    
    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(MaSignal, self).__init__()
        
        self.fastWindow = 5
        self.slowWindow = 20
        
        self.bg = BarGenerator(self.onBar, 5, self.onFiveBar)
        self.am = ArrayManager()        
        
    #----------------------------------------------------------------------
    def onTick(self, tick):
        """Tick更新"""
        self.bg.updateTick(tick)
        
    #----------------------------------------------------------------------
    def onBar(self, bar):
        """K线更新"""
        self.bg.updateBar(bar)
    
    #----------------------------------------------------------------------
    def onFiveBar(self, bar):
        """5分钟K线更新"""
        self.am.updateBar(bar)
        
        if not self.am.inited:
            self.setSignalPos(0)
            
        fastMa = self.am.sma(self.fastWindow)
        slowMa = self.am.sma(self.slowWindow)
        
        if fastMa > slowMa:
            self.setSignalPos(1)
        elif fastMa < slowMa:
            self.setSignalPos(-1)
        else:
            self.setSignalPos(0)
    

########################################################################
class MultiSignalStrategy(TargetPosTemplate):
    """跨时间周期交易策略"""
    className = 'MultiSignalStrategy'
    author = u'用Python的交易员'

    # 策略参数
    initDays = 10           # 初始化数据所用的天数
    fixedSize = 1           # 每次交易的数量

    # 策略变量
    signalPos = {}          # 信号仓位
    
    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol']    

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'signalPos',
               'targetPos']

    # 同步列表，保存了需要保存到数据库的变量名称
    syncList = ['pos']

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(MultiSignalStrategy, self).__init__(ctaEngine, setting)

        self.rsiSignal = RsiSignal()
        self.cciSignal = CciSignal()
        self.maSignal = MaSignal()
        
        self.signalPos = {
            "rsi": 0,
            "cci": 0,
            "ma": 0
        }
        
    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略初始化' %self.name)

        # 载入历史数据，并采用回放计算的方式初始化策略数值
        initData = self.loadBar(self.initDays)
        for bar in initData:
            self.onBar(bar)

        self.putEvent()

    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略启动' %self.name)
        self.putEvent()

    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略停止' %self.name)
        self.putEvent()

    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        super(MultiSignalStrategy, self).onTick(tick)
        
        self.rsiSignal.onTick(tick)
        self.cciSignal.onTick(tick)
        self.maSignal.onTick(tick)
        
    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        super(MultiSignalStrategy, self).onBar(bar)
        
        self.rsiSignal.onBar(bar)
        self.cciSignal.onBar(bar)
        self.maSignal.onBar(bar)
        
        self.signalPos['rsi'] = self.rsiSignal.getSignalPos()
        self.signalPos['cci'] = self.cciSignal.getSignalPos()
        self.signalPos['ma'] = self.maSignal.getSignalPos()
        
        targetPos = 0
        for v in self.signalPos.values():
            targetPos += v
            
        self.setTargetPos(targetPos)
        
    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        super(MultiSignalStrategy, self).onOrder(order)

    #----------------------------------------------------------------------
    def onTrade(self, trade):
        # 发出状态更新事件
        self.putEvent()

    #----------------------------------------------------------------------
    def onStopOrder(self, so):
        """停止单推送"""
        pass
    
def runBacktesting():
    from vnpy.trader.app.ctaStrategy.ctaBacktesting import BacktestingEngine, MINUTE_DB_NAME
    # 创建回测引擎
    engine = BacktestingEngine()
    
    # 设置引擎的回测模式为K线
    engine.setBacktestingMode(engine.BAR_MODE)

    # 设置回测用的数据起始日期
    engine.setStartDate('20110801')
    
    # 设置产品相关参数
    engine.setCapital(10000)
    engine.setSlippage(1)     # 股指1跳
    engine.setRate(1.0/10000)   # 万0.3
    engine.setSize(10)         # 股指合约大小 
    engine.setPriceTick(1)    # 股指最小价格变动
    
    # 设置使用的历史数据库
    engine.setDatabase(MINUTE_DB_NAME, 'rb0000')
    engine.stratName = 'MultiSignalStrategy'
    engine.symbol = 'rb0000'    
    
    # 在引擎中创建策略对象
    d = {}
    engine.initStrategy(MultiSignalStrategy, d)
    
    # 开始跑回测
    engine.runBacktesting()
    
    # 显示回测结果
    #engine.showBacktestingResult()
    #engine.showDailyResult()
    engine.saveDailyResult()
                
def runOptimization():
    from vnpy.trader.app.ctaStrategy.ctaBacktesting import BacktestingEngine, MINUTE_DB_NAME, OptimizationSetting
    
    # 创建回测引擎
    engine = BacktestingEngine()
    
    # 设置引擎的回测模式为K线
    engine.setBacktestingMode(engine.BAR_MODE)

    # 设置回测用的数据起始日期
    engine.setStartDate('20110801')
    
    # 设置产品相关参数
    engine.setCapital(100000)
    engine.setSlippage(1)     # 股指1跳
    engine.setRate(1.0/10000)   # 万0.3
    engine.setSize(10)         # 股指合约大小 
    engine.setPriceTick(1)    # 股指最小价格变动
    
    # 设置使用的历史数据库
    engine.setDatabase(MINUTE_DB_NAME, 'rb0000')
    engine.stratName = 'MultiSignalStrategy'
    engine.symbol = 'rb0000'
    
    # 跑优化
    setting = OptimizationSetting()                 # 新建一个优化任务设置对象
    setting.setOptimizeTarget('totalNetPnl')            # 设置优化排序的目标是策略净盈利 sharpeRatio totalNetPnl endBalance
    
    #setting.addParameter('stop_loss', 10, 100, 5)    # 增加第一个优化参数atrLength，起始12，结束20，步进2
    setting.addParameter('stop_loss', 65)  
    
    #setting.addParameter('bollDev', 1, 5, 0.5)        # 增加第二个优化参数atrMa，起始20，结束30，步进5
    setting.addParameter('bollDev', 2.5)
    
    setting.addParameter('bollWindow', 10, 100, 5) 
    #setting.addParameter('bollWindow', 5)            # 增加一个固定数值的参数
    
    # 性能测试环境：I7-3770，主频3.4G, 8核心，内存16G，Windows 7 专业版
    # 测试时还跑着一堆其他的程序，性能仅供参考
    import time    
    start = time.time()
    
    # 运行单进程优化函数，自动输出结果，耗时：359秒
    #engine.runOptimization(BollingerStrategy, setting)            
    
    # 多进程优化，耗时：89秒
    #engine.runParallelOptimization(BollingerStrategy, setting)
    engine.saveParallelOptimization(MultiSignalStrategy, setting)
         
        
    print u'耗时：%s' %(time.time()-start)   
            
if __name__ == '__main__':
    runBacktesting()
    #runOptimization()