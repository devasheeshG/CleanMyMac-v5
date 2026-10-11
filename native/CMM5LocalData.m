#import <Foundation/Foundation.h>
#import <objc/runtime.h>

static BOOL isTestGroup(NSString *group) {
    static NSSet<NSString *> *groups;
    static dispatch_once_t once;
    dispatch_once(&once, ^{
        groups = [NSSet setWithArray:@[
            @"S8EX82NJP6.com.macpaw.CleanMyMac5", @"S8EX82NJP6.com.macpaw.CleanMyMac5.CLI", @"S8EX82NJP6.com.macpaw.CleanMyMac4",
            @"PATCHCMM05.com.macpaw.CleanMyMac5", @"PATCHCMM05.com.macpaw.CleanMyMac5.CLI", @"PATCHCMM05.com.macpaw.CleanMyMac4"
        ]];
    });
    return group != nil && [groups containsObject:group];
}

@interface NSFileManager (CMM5LocalData)
- (NSURL *)cmm5_localContainerURL:(NSString *)group;
@end
@implementation NSFileManager (CMM5LocalData)
- (NSURL *)cmm5_localContainerURL:(NSString *)group {
    if (!isTestGroup(group)) return [self cmm5_localContainerURL:group];
    NSURL *base = [[NSURL fileURLWithPath:NSHomeDirectory() isDirectory:YES]
        URLByAppendingPathComponent:@"Library/Application Support/CleanMyMacPatched/Groups" isDirectory:YES];
    NSURL *folder = [base URLByAppendingPathComponent:group isDirectory:YES];
    NSError *error = nil;
    if (![self createDirectoryAtURL:folder withIntermediateDirectories:YES attributes:nil error:&error]) {
        fprintf(stderr, "CMM5LocalData: cannot create local container (code %ld)\n", (long)error.code);
        return nil;
    }
    return folder;
}
@end

@interface NSUserDefaults (CMM5LocalData)
- (instancetype)cmm5_localInitWithSuiteName:(NSString *)suite __attribute__((objc_method_family(init)));
@end
@implementation NSUserDefaults (CMM5LocalData)
- (instancetype)cmm5_localInitWithSuiteName:(NSString *)suite {
    if (isTestGroup(suite)) suite = [@"com.devasheesh.CleanMyMacPatched." stringByAppendingString:suite];
    return [self cmm5_localInitWithSuiteName:suite];
}
@end

__attribute__((constructor)) static void initializeLocalData(void) {
    @autoreleasepool {
        Method container = class_getInstanceMethod([NSFileManager class], @selector(containerURLForSecurityApplicationGroupIdentifier:));
        Method localContainer = class_getInstanceMethod([NSFileManager class], @selector(cmm5_localContainerURL:));
        Method suite = class_getInstanceMethod([NSUserDefaults class], @selector(initWithSuiteName:));
        Method localSuite = class_getInstanceMethod([NSUserDefaults class], @selector(cmm5_localInitWithSuiteName:));
        if (!container || !localContainer || !suite || !localSuite) {
            fprintf(stderr, "CMM5LocalData: required Foundation methods unavailable\n");
            return;
        }
        method_exchangeImplementations(container, localContainer);
        method_exchangeImplementations(suite, localSuite);
        fprintf(stderr, "CMM5LocalData: local data adapter loaded\n");
    }
}
