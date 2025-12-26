--[[----------------------------------------------------------------------------

Info.lua
Simple Album Upload Plugin for Adobe Lightroom

Allows direct upload of photos from Lightroom to a Simple Album server.

------------------------------------------------------------------------------]]

return {
    LrSdkVersion = 6.0,
    LrSdkMinimumVersion = 6.0,
    
    LrToolkitIdentifier = 'com.simplealbum.export',
    LrPluginName = "Simple Album Upload",
    
    LrExportServiceProvider = {
        title = "Simple Album Server",
        file = 'ExportServiceProvider.lua',
    },
    
    VERSION = { major=1, minor=0, revision=0, build=1 },
}
