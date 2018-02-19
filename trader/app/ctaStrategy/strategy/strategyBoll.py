# encoding: UTF-8
#作者：尔鸫
#链接：https://zhuanlan.zhihu.com/p/33264783
#来源：知乎
#著作权归作者所有。商业转载请联系作者获得授权，非商业转载请注明出处。

from __future__ import division

from vnpy.trader.vtObject import VtBarData
from vnpy.trader.vtConstant import EMPTY_STRING
from vnpy.trader.app.ctaStrategy.ctaTemplate import (CtaTemplate, 
                                                     BarGenerator, 
                                                     ArrayManager)
class BollingerStrategy(CtaTemplate):
    """基于布林通道的交易策略"""
    className = 'BollingerStrategy'
    author = u'用Python的交易员'

    # 策略参数
    bollWindow = 40                     # 布林通道窗口数
    bollDev = 3                       # 布林通道的偏差
    #cciWindow = 10                      # CCI窗口数
    #atrWindow = 30                      # ATR窗口数
    #slMultiplier = 5.2                  # 计算止损距离的乘数
    initDays = 10                       # 初始化数据所用的天数
    fixedSize = 1                       # 每次交易的数量
    stop_loss = 10 #

    # 策略变量
    bollUp = 0                          # 布林通道上轨
    bollDown = 0                        # 布林通道下轨
    #cciValue = 0                        # CCI指标数值
    #atrValue = 0                        # ATR指标数值
    
    max_price = 0                  # 持仓期内的最高点
    min_price = 0                   # 持仓期内的最低点
    longStop = 0                        # 多头止损
    shortStop = 0                       # 空头止损

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'bollWindow',
                 'bollDev',
                 'initDays',
                 'fixedSize',
                 'stop_loss']    

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'bollUp',
               'bollDown',
               'max_price',
               'min_price',
               'longStop',
               'shortStop'
               ]  

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(BollingerStrategy, self).__init__(ctaEngine, setting)
        
        self.bm = BarGenerator(self.onBar, 15, self.onXminBar)        # 创建K线合成器对象
        self.am = ArrayManager()
        
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
        self.bm.updateTick(tick)

    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        self.bm.updateBar(bar)
    
    #----------------------------------------------------------------------
    def onXminBar(self, bar):
        """收到X分钟K线"""
        # 全撤之前发出的委托
        self.cancelAll()
    
        # 保存K线数据
        am = self.am
        
        am.updateBar(bar)
        
        if not am.inited:
            return
        
        # 计算指标数值
        self.bollUp, self.bollDown = am.boll(self.bollWindow, self.bollDev)
        
        # 判断是否要进行交易
    
        # 当前无仓位，发送开仓委托
        if self.pos == 0:   
            
            if bar.close > self.bollUp:
                self.buy(bar.close+100, self.fixedSize)
                self.max_price = bar.close
                
            elif bar.close < self.bollDown:
                self.short(self.bollDown-100, self.fixedSize)
                self.min_price = bar.close
    
        # 持有多头仓位
        elif self.pos > 0:
            self.max_price = max(self.max_price, bar.close)
            self.longStop = self.max_price - self.stop_loss
            
            self.sell(self.longStop, abs(self.pos), True)
    
        # 持有空头仓位
        elif self.pos < 0:
            self.min_price = min(self.min_price, bar.close)
            self.shortStop = self.min_price + self.stop_loss
            
            self.cover(self.shortStop, abs(self.pos), True)
    
        # 发出状态更新事件
        self.putEvent()        

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
    d = {'stop_loss':45,'bollDev':2, 'bollWindow':25}
    engine.initStrategy(BollingerStrategy, d)
    
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
    engine.stratName = 'BollingerStrategy'
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
    engine.saveParallelOptimization(BollingerStrategy, setting)
     
    
    print u'耗时：%s' %(time.time()-start)    
if __name__ == '__main__':
    runBacktesting()
    #runOptimization()
