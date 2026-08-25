use framework "Foundation"
use framework "AppKit"

property visibleNotifications : {}
property notificationLogPath : missing value
property notificationHandlerPath : missing value
property notificationHandlerLogPath : missing value
property notificationHandlerPythonPath : missing value

on run
	my initialiseLogPath()
end run

on idle
	if notificationLogPath is missing value or notificationHandlerPath is missing value or notificationHandlerPythonPath is missing value then my initialiseLogPath()

	set notificationsNow to {}
	set notificationSignaturesNow to {}

	tell application "System Events"
		if not (exists process "NotificationCenter") then return 1

		tell process "NotificationCenter"
			repeat with notificationWindow in every window
				try
					-- A Notification Center window can contain several notifications and widgets.
					set windowContents to entire contents of notificationWindow

					-- Notification cards can be nested inside a stack, so find them at any depth.
					repeat with notificationContainer in windowContents
						try
							set containerSubrole to subrole of notificationContainer as text

							if containerSubrole is "AXNotificationCenterBanner" or containerSubrole is "AXNotificationCenterAlert" then
								set notificationFields to my fieldsOfContainer(notificationContainer)

								if notificationFields is not missing value then
									set notificationSignature to item 1 of notificationFields

									if notificationSignaturesNow does not contain notificationSignature then
										set end of notificationSignaturesNow to notificationSignature
										set end of notificationsNow to notificationFields
									end if
								end if
							end if
						on error
							-- Ignore elements that do not expose a subrole or contents.
						end try
					end repeat

					-- Calendar, weather, and other widgets are direct sections of a scroll area.
					repeat with scrollContainer in windowContents
						try
							if role of scrollContainer is "AXScrollArea" then
								repeat with sectionContainer in every UI element of scrollContainer
									set containsNotification to false

									try
										set sectionSubrole to subrole of sectionContainer as text
										if sectionSubrole is "AXNotificationCenterBanner" or sectionSubrole is "AXNotificationCenterAlert" then
											set containsNotification to true
										end if
									end try

									if not containsNotification then
										try
											set sectionContents to entire contents of sectionContainer

											repeat with childElement in sectionContents
												try
													set childSubrole to subrole of childElement as text
													if childSubrole is "AXNotificationCenterBanner" or childSubrole is "AXNotificationCenterAlert" then
														set containsNotification to true
														exit repeat
													end if
												on error
												end try
											end repeat
										on error
										end try
									end if

									if not containsNotification then
										set sectionFields to my fieldsOfContainer(sectionContainer)

										if sectionFields is not missing value then
											set sectionSignature to item 1 of sectionFields

											if notificationSignaturesNow does not contain sectionSignature then
												set end of notificationSignaturesNow to sectionSignature
												set end of notificationsNow to sectionFields
											end if
										end if
								end if
								end repeat
							end if
						on error
							-- Ignore scroll areas without accessible sections.
						end try
					end repeat
				on error
					-- Ignore Notification Center windows without accessible contents.
				end try
			end repeat
		end tell
	end tell

	repeat with notificationFields in notificationsNow
		set notificationFields to contents of notificationFields
		set notificationSignature to item 1 of notificationFields

		if visibleNotifications does not contain notificationSignature then
			my appendNotification(notificationFields)
		end if
	end repeat

	set visibleNotifications to notificationSignaturesNow
	return 1
end idle

on initialiseLogPath()
	set applicationPath to current application's NSBundle's mainBundle()'s bundlePath() as text
	set applicationDirectory to current application's NSString's stringWithString:applicationPath
	set applicationDirectory to applicationDirectory's stringByDeletingLastPathComponent()
	set notificationLogPath to (applicationDirectory's stringByAppendingPathComponent:"notification") as text

	set subscriberDirectory to current application's NSString's stringWithString:applicationDirectory
	set subscriberDirectory to subscriberDirectory's stringByDeletingLastPathComponent()
	set notificationHandlerPath to (subscriberDirectory's stringByAppendingPathComponent:"handle_notification.py") as text
	set notificationHandlerLogPath to (subscriberDirectory's stringByAppendingPathComponent:"handler.log") as text
	set notificationHandlerPythonPath to (subscriberDirectory's stringByAppendingPathComponent:".venv/bin/python3") as text
end initialiseLogPath

on fieldsOfContainer(accessibilityContainer)
	set containerTexts to my textsOfContainer(accessibilityContainer)
	if (count of containerTexts) is 0 then return missing value

	set notificationHeader to item 1 of containerTexts as text
	set notificationDatetime to ""
	set bodyEndIndex to count of containerTexts

	if bodyEndIndex > 1 then
		set possibleDatetime to item bodyEndIndex of containerTexts as text
		if my looksLikeNotificationDatetime(possibleDatetime) then
			set notificationDatetime to possibleDatetime
			set bodyEndIndex to bodyEndIndex - 1
		end if
	end if

	set notificationBody to ""
	if bodyEndIndex > 1 then set notificationBody to my joinText(items 2 thru bodyEndIndex of containerTexts, " | ")

	set applicationIdentity to my applicationIdentityOfContainer(accessibilityContainer)
	set applicationIdentifier to item 1 of applicationIdentity
	set applicationName to item 2 of applicationIdentity
	set notificationIdentifier to my notificationIdOfContainer(accessibilityContainer)

	-- Do not include relative notification time: it changes while the card is visible.
	set notificationSignature to applicationIdentifier & "|||" & notificationIdentifier & "|||" & notificationHeader & "|||" & notificationBody
	return {notificationSignature, applicationIdentifier, applicationName, notificationIdentifier, notificationDatetime, notificationHeader, notificationBody}
end fieldsOfContainer

on textsOfContainer(accessibilityContainer)
	set containerTexts to {}

	tell application "System Events"
		try
			set containerContents to entire contents of accessibilityContainer

			repeat with uiElement in containerContents
				try
					if role of uiElement is "AXStaticText" then
						set elementText to value of uiElement

						if elementText is missing value or elementText is "" then
							set elementText to name of uiElement
						end if

						if elementText is not missing value and elementText is not "" then
							set elementText to my normaliseText(elementText as text)

							if elementText is not "" and containerTexts does not contain elementText then
								set end of containerTexts to elementText
							end if
						end if
					end if
				on error
					-- Some accessibility elements do not expose role/value/name.
				end try
			end repeat
			on error
				return {}
			end try
		end tell

	return containerTexts
end textsOfContainer

on applicationIdentityOfContainer(accessibilityContainer)
	set bundleIdentifier to ""
	tell application "System Events"
		try
			set stackingIdentifier to value of attribute "AXStackingIdentifier" of accessibilityContainer as text
		on error
			return {"unknown", "unknown"}
		end try
	end tell

	set identifierPrefix to "bundleIdentifier="
	if stackingIdentifier starts with identifierPrefix then
		set bundleIdentifier to text ((length of identifierPrefix) + 1) thru -1 of stackingIdentifier
	end if

	if bundleIdentifier is "" then return {"unknown", "unknown"}

	try
		set applicationURL to current application's NSWorkspace's sharedWorkspace()'s URLForApplicationWithBundleIdentifier:bundleIdentifier

		if applicationURL is not missing value then
			set applicationBundle to current application's NSBundle's bundleWithURL:applicationURL
			set applicationName to applicationBundle's objectForInfoDictionaryKey:"CFBundleDisplayName"
			if applicationName is missing value then set applicationName to applicationBundle's objectForInfoDictionaryKey:"CFBundleName"

			if applicationName is not missing value and (applicationName as text) is not "" then
				return {bundleIdentifier, applicationName as text}
			end if
		end if
	on error
	end try

	-- A bundle identifier is still more useful than losing the sender completely.
	return {bundleIdentifier, bundleIdentifier}
end applicationIdentityOfContainer

on notificationIdOfContainer(accessibilityContainer)
	tell application "System Events"
		try
			set notificationIdentifier to value of attribute "AXIdentifier" of accessibilityContainer as text
			if notificationIdentifier is not "" then return notificationIdentifier
		on error
		end try
	end tell

	return "unknown"
end notificationIdOfContainer

on looksLikeNotificationDatetime(candidateText)
	set dateText to current application's NSString's stringWithString:candidateText
	set dateText to dateText's lowercaseString() as text

	if dateText contains " назад" or dateText contains " ago" then return true
	if dateText is in {"сейчас", "только что", "сегодня", "вчера", "позавчера", "now", "today", "yesterday"} then return true
	if dateText is in {"понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"} then return true

	set timePatterns to {"^[0-2]?[0-9]:[0-5][0-9]$", "^[0-3]?[0-9][./-][0-1]?[0-9]([./-][0-9]{2,4})?$"}
	repeat with timePattern in timePatterns
		set datePredicate to current application's NSPredicate's predicateWithFormat:"SELF MATCHES[c] %@" argumentArray:{timePattern as text}
		if (datePredicate's evaluateWithObject:dateText) as boolean then return true
	end repeat

	return false
end looksLikeNotificationDatetime

on appendNotification(notificationFields)
	set timestamp to «event sysoexec» "/bin/date '+%Y-%m-%d %H:%M:%S'"
	set jsonObject to current application's NSMutableDictionary's dictionary()
	jsonObject's setObject:timestamp forKey:"datetime"
	jsonObject's setObject:(item 2 of notificationFields) forKey:"appId"
	jsonObject's setObject:(item 3 of notificationFields) forKey:"appName"
	jsonObject's setObject:(item 4 of notificationFields) forKey:"notificationId"
	jsonObject's setObject:(item 5 of notificationFields) forKey:"notificationDatetime"
	jsonObject's setObject:(item 6 of notificationFields) forKey:"notificationHeader"
	jsonObject's setObject:(item 7 of notificationFields) forKey:"notificationBody"

	set jsonData to current application's NSJSONSerialization's dataWithJSONObject:jsonObject options:0 |error|:(missing value)
	set jsonLine to current application's NSString's alloc()'s initWithData:jsonData encoding:(current application's NSUTF8StringEncoding)
	set jsonText to jsonLine as text

	-- Keep the JSONL audit log before dispatching the notification.
	«event sysoexec» "/usr/bin/printf '%s\\n' " & quoted form of jsonText & " >> " & quoted form of notificationLogPath

	-- Run asynchronously so draw.py animations do not block Notification Center polling.
	try
		set handlerCommand to quoted form of notificationHandlerPythonPath & " " & quoted form of notificationHandlerPath & " " & quoted form of jsonText & " >> " & quoted form of notificationHandlerLogPath & " 2>&1 &"
		«event sysoexec» handlerCommand
	on error
		-- A handler failure must not prevent subsequent notifications from being logged.
	end try
end appendNotification

on joinText(textItems, separator)
	set previousDelimiters to AppleScript's text item delimiters
	set AppleScript's text item delimiters to separator
	set joinedText to textItems as text
	set AppleScript's text item delimiters to previousDelimiters
	return joinedText
end joinText

on normaliseText(sourceText)
	set sourceText to my replaceText(return, " ", sourceText)
	set sourceText to my replaceText(linefeed, " ", sourceText)
	return sourceText
end normaliseText

on replaceText(searchText, replacementText, sourceText)
	set previousDelimiters to AppleScript's text item delimiters
	set AppleScript's text item delimiters to searchText
	set textParts to text items of sourceText
	set AppleScript's text item delimiters to replacementText
	set replacedText to textParts as text
	set AppleScript's text item delimiters to previousDelimiters
	return replacedText
end replaceText
