# Prompts

## SpecHub specific

The spec and the Postman collection both seem very incomplete, not containing all possible icons and other character restrictions. Can you scan the backend API code to find out what additional endpoints and capabilities regarding icons and character restrictions there are and update the spec accordingly?

Can you create a mock server and environment for this collection?

Can you create a new collection and data file that mixes allowed messages with allowed icons and invalid messages and test whether the expected results occur?

## Mock specific

can you add two examples to the data file @"data-file.csv" - one succeeding and one failing, that is greeting company SAP with valid characters on the LED and once with invalid ones - also add the samples to our mock server in @"Mock Answers LED Display API"

## MCP specific

Can you provide a fancy greeting with the current weather in SF to the LED?

Can you provide a less fancy greeting with the current weather in SF to the LED that does not contain any special characters?

This API is not optimal for AI agents yet because its specification does not mention that you cannot use any special characters but the ones returned in the predefined icons call. Can you make this crystal clear in the documentation of the collection and its requests?

Can you fetch the led display collection from postman (tagged led) and adopt this mcp server to work better based on its documentation? only change the mcp tool descriptions so that agents know how to use the api properly.