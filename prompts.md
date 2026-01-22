# Prompts

## SpecHub specific

The spec and the Postman collection both seem very incomplete, not containing all possible icons and other character restrictions. Can you scan the backend API code to find out what additional endpoints and capabilities regarding icons and character restrictions there are and update the spec accordingly?

Can you create a mock server and environment for this collection?

Can you create a new collection and data file that mixes allowed messages with allowed icons and invalid messages and test whether the expected results occur?

## Mock specific

Can you create a new collection and data file that mixes allowed messages with allowed icons and invalid messages and test whether the expected results occur?

Can you add two examples to the data file @"data-file.csv" - one succeeding and one failing, that is greeting company Uber with valid characters on the LED and once with invalid ones - also add the samples to our mock server in @"Mock Answers LED Display API"

## Request Chaining example

Can you create a new collection called "Request Chaining example" that first gets the predefined icons in its first request, then save those to a collection variable and then use that collection variable in the subsequent request to display three random icons from the first request on the LED? Use the @"Final LED Display API" as reference collection for the needed requests

### CI / CD

Can you change the spec validation workflow that it does not reach out to the cloud but lint the @"Final LED Display API" from this repository instead?

Can you create a GitHub Actions workflow that triggers on every repo push and runs the @"LED Display API - Data File Test Suite" with the data file @"data-file.csv" and the environment @"LED Display Mock Environment"

## MCP specific

Can you provide a fancy greeting with the current weather in SF to the LED?

Can you provide a less fancy greeting with the current weather in SF to the LED that does not contain any special characters?

This API is not optimal for AI agents yet because its specification does not mention that you cannot use any special characters but the ones returned in the predefined icons call. Can you make this crystal clear in the documentation of the collection and its requests?

Can you fetch the led display collection from postman (tagged led) and adopt this mcp server to work better based on its documentation? only change the mcp tool descriptions so that agents know how to use the api properly.