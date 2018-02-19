# encoding: UTF-8

"""
一个跨时间周期的策略，基于15分钟K线判断趋势方向，并使用5分钟RSI指标作为入场
"""

from vnpy.trader.vtObject import VtBarData
from vnpy.trader.vtConstant import EMPTY_STRING
from vnpy.trader.app.ctaStrategy.ctaTemplate import (CtaTemplate, 
                                                     BarGenerator, 
                                                     ArrayManager)


########################################################################
class MultiTimeframeStrategy(CtaTemplate):
    """跨时间周期交易策略"""
    className = 'MultiTimeframeStrategy'
    author = u'用Python的交易员'

    # 策略参数
    rsiSignal = 20          # RSI信号阈值
    rsiWindow = 14          # RSI窗口
    fastWindow = 5          # 快速均线窗口
    slowWindow = 20         # 慢速均线窗口
    
    initDays = 10           # 初始化数据所用的天数
    fixedSize = 1           # 每次交易的数量

    # 策略变量
    rsiValue = 0                        # RSI指标的数值
    rsiLong = 0                         # RSI买开阈值
    rsiShort = 0                        # RSI卖开阈值
    fastMa = 0                          # 5分钟快速均线
    slowMa = 0                          # 5分钟慢速均线
    maTrend = 0                         # 均线趋势，多头1，空头-1
    
    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'rsiSignal',
                 'rsiWindow',
                 'fastWindow',
                 'slowWindow']    

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'rsiValue',
               'rsiLong',
               'rsiShort',
               'fastMa',
               'slowMa',
               'maTrend']  
    
    # 同步列表，保存了需要保存到数据库的变量名称
    syncList = ['pos']

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(MultiTimeframeStrategy, self).__init__(ctaEngine, setting)
        
        self.rsiLong = 50 + self.rsiSignal
        self.rsiShort = 50 - self.rsiSignal
        
        # 创建K线合成器对象
        self.bg5 = BarGenerator(self.onBar, 5, self.on5MinBar)
        self.am5 = ArrayManager()
        
        self.bg15 = BarGenerator(self.onBar, 15, self.on15MinBar)
        self.am15 = ArrayManager()
        
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
        # 只需要要在一个BM中合成1分钟K线
        self.bg5.updateTick(tick)

    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        # 基于15分钟判断趋势过滤，因此先更新
        self.bg15.updateBar(bar)
        
        # 基于5分钟判断
        self.bg5.updateBar(bar)
        
    #----------------------------------------------------------------------
    def on5MinBar(self, bar):
        """5分钟K线"""
        self.cancelAll()

        # 保存K线数据
        self.am5.updateBar(bar)
        if not self.am5.inited:
            return
        
        # 如果15分钟数据尚未初始化完毕，则直接返回
        if not self.maTrend:
            return

        # 计算指标数值
        self.rsiValue = self.am5.rsi(self.rsiWindow)

        # 判断是否要进行交易
        
        # 当前无仓位
        if self.pos == 0:
            if self.maTrend > 0 and self.rsiValue >= self.rsiLong:
                self.buy(bar.close+5, self.fixedSize)
                
            elif self.maTrend < 0 and self.rsiValue <= self.rsiShort:
                self.short(bar.close-5, self.fixedSize)

        # 持有多头仓位
        elif self.pos > 0:
            if self.maTrend < 0 or self.rsiValue < 50:
                self.sell(bar.close-5, abs(self.pos))
            
        # 持有空头仓位
        elif self.pos < 0:
            if self.maTrend > 0 or self.rsiValue > 50:
                self.cover(bar.close+5, abs(self.pos))

        # 发出状态更新事件
        self.putEvent()        
    
    #----------------------------------------------------------------------
    def on15MinBar(self, bar):
        """15分钟K线推送"""
        self.am15.updateBar(bar)
        
        if not self.am15.inited:
            return
        
        # 计算均线并判断趋势
        self.fastMa = self.am15.sma(self.fastWindow)
        self.slowMa = self.am15.sma(self.slowWindow)
        
        if self.fastMa > self.slowMa:
            self.maTrend = 1
        else:
            self.maTrend = -1

    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

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
    
    # 在引擎中创建策略对象
    d = {}
    engine.initStrategy(MultiTimeframeStrategy, d)
    
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
    engine.stratName = 'MultiTimeframeStrategy'
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
    engine.saveParallelOptimization(MultiTimeframeStrategy, setting)
         
        
    print u'耗时：%s' %(time.time()-start)   
        
if __name__ == '__main__':
    runBacktesting()
    #runOptimization()