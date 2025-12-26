--[[----------------------------------------------------------------------------

ExportServiceProvider.lua
Export service provider for Simple Album Upload Plugin

This script handles the export and upload of images from Lightroom to 
a Simple Album server.

------------------------------------------------------------------------------]]

-- Lightroom SDK
local LrDialogs = import 'LrDialogs'
local LrErrors = import 'LrErrors'
local LrFileUtils = import 'LrFileUtils'
local LrHttp = import 'LrHttp'
local LrPathUtils = import 'LrPathUtils'
local LrView = import 'LrView'
local LrBinding = import 'LrBinding'

--------------------------------------------------------------------------------
-- Export Service Provider Configuration

local exportServiceProvider = {}

-- Plugin metadata
exportServiceProvider.supportsIncrementalPublish = false
exportServiceProvider.allowFileFormats = { 'JPEG', 'PNG' }
exportServiceProvider.allowColorSpaces = { 'sRGB', 'AdobeRGB' }
exportServiceProvider.hidePrintResolution = true

--------------------------------------------------------------------------------
-- Export Dialog Sections

function exportServiceProvider.sectionsForTopOfDialog( f, propertyTable )
    local bind = LrView.bind
    local share = LrView.share
    
    -- Initialize default values if not set
    if propertyTable.serverUrl == nil then
        propertyTable.serverUrl = "https://images.yourdomain.com"
    end
    
    if propertyTable.apiKey == nil then
        propertyTable.apiKey = ""
    end
    
    if propertyTable.uploadPath == nil then
        propertyTable.uploadPath = "lightroom/"
    end
    
    return {
        {
            title = "Simple Album Server Settings",
            
            synopsis = bind { key = 'serverUrl', object = propertyTable },
            
            f:row {
                f:static_text {
                    title = "Server URL:",
                    alignment = 'right',
                    width = share 'labelWidth'
                },
                
                f:edit_field {
                    value = bind 'serverUrl',
                    immediate = true,
                    width_in_chars = 40,
                    tooltip = "The URL of your Simple Album server (e.g., https://images.yourdomain.com)"
                },
            },
            
            f:row {
                f:static_text {
                    title = "API Key:",
                    alignment = 'right',
                    width = share 'labelWidth'
                },
                
                f:password_field {
                    value = bind 'apiKey',
                    immediate = true,
                    width_in_chars = 40,
                    tooltip = "Your Simple Album server API key for upload authentication"
                },
            },
            
            f:row {
                f:static_text {
                    title = "Upload Path:",
                    alignment = 'right',
                    width = share 'labelWidth'
                },
                
                f:edit_field {
                    value = bind 'uploadPath',
                    immediate = true,
                    width_in_chars = 40,
                    tooltip = "Destination path on the server (relative to image_root). Use / to upload to root."
                },
            },
            
            f:row {
                f:static_text {
                    title = "",
                    width = share 'labelWidth'
                },
                
                f:static_text {
                    title = "Images will be uploaded to: <server>/<upload_path>/<filename>",
                    fill_horizontal = 1,
                },
            },
        },
    }
end

--------------------------------------------------------------------------------
-- Export Processing

function exportServiceProvider.processRenderedPhotos( functionContext, exportContext )
    local exportSession = exportContext.exportSession
    local exportParams = exportContext.propertyTable
    
    -- Get settings
    local serverUrl = exportParams.serverUrl
    local apiKey = exportParams.apiKey
    local uploadPath = exportParams.uploadPath
    
    -- Validate settings
    if not serverUrl or serverUrl == "" then
        LrErrors.throwUserError( "Server URL is required. Please enter your Simple Album server URL." )
    end
    
    if not apiKey or apiKey == "" then
        LrErrors.throwUserError( "API Key is required. Please enter your Simple Album API key." )
    end
    
    -- Ensure serverUrl doesn't end with slash
    if string.sub(serverUrl, -1) == "/" then
        serverUrl = string.sub(serverUrl, 1, -2)
    end
    
    -- Ensure uploadPath ends with slash if not empty
    if uploadPath ~= "" and string.sub(uploadPath, -1) ~= "/" then
        uploadPath = uploadPath .. "/"
    end
    
    -- Remove leading slash from uploadPath
    if string.sub(uploadPath, 1, 1) == "/" then
        uploadPath = string.sub(uploadPath, 2)
    end
    
    -- Configure progress display
    local nPhotos = exportSession:countRenditions()
    local progressScope = exportContext:configureProgress {
        title = nPhotos > 1 and "Uploading " .. nPhotos .. " photos to Simple Album"
                             or "Uploading one photo to Simple Album",
    }
    
    -- Process each photo
    for i, rendition in exportContext:renditions{ stopIfCanceled = true } do
        
        -- Update progress
        progressScope:setPortionComplete( i - 1, nPhotos )
        
        if not rendition.wasSkipped then
            
            local success, pathOrMessage = rendition:waitForRender()
            
            if success then
                -- Get the rendered photo file path
                local photoPath = pathOrMessage
                local filename = LrPathUtils.leafName( photoPath )
                
                -- Read the image file
                local fileContent = LrFileUtils.readFile( photoPath )
                
                if not fileContent then
                    rendition:renditionIsDone( false, "Could not read rendered image file." )
                else
                    -- Construct upload URL (without API key in URL for better security)
                    local uploadUrl = serverUrl .. "/" .. uploadPath .. filename
                    
                    -- Determine content type based on file extension
                    local contentType = "image/jpeg"
                    local ext = string.lower(LrPathUtils.extension(filename))
                    if ext == "png" then
                        contentType = "image/png"
                    elseif ext == "jpg" or ext == "jpeg" then
                        contentType = "image/jpeg"
                    end
                    
                    -- Upload the file with API key in Authorization header
                    local result = LrHttp.post( uploadUrl, fileContent, {
                        { field = "Content-Type", value = contentType },
                        { field = "Authorization", value = "Bearer " .. apiKey },
                    })
                    
                    -- Check upload status
                    if result then
                        -- Try to parse JSON response
                        local success_flag = string.find(result, '"success"%s*:%s*true')
                        
                        if success_flag then
                            rendition:renditionIsDone( true )
                        else
                            -- Check for error message in response
                            local error_msg = string.match(result, '"error"%s*:%s*"([^"]+)"')
                            if error_msg then
                                rendition:renditionIsDone( false, "Upload failed: " .. error_msg )
                            else
                                rendition:renditionIsDone( false, "Upload failed: " .. result )
                            end
                        end
                    else
                        rendition:renditionIsDone( false, "Upload failed: No response from server" )
                    end
                end
                
                -- Clean up rendered file if it's a temporary export
                -- Note: Lightroom handles cleanup of temporary files automatically
                
            else
                -- Rendering failed
                rendition:renditionIsDone( false, pathOrMessage )
            end
        end
    end
    
    progressScope:done()
end

--------------------------------------------------------------------------------

return exportServiceProvider
