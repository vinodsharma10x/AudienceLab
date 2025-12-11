# Get shared voices

GET https://api.elevenlabs.io/v1/shared-voices

Retrieves a list of shared voices.

## OpenAPI Specification

```yaml
openapi: 3.1.1
info:
  title: Get shared voices
  version: endpoint_voices.get_shared
paths:
  /v1/shared-voices:
    get:
      operationId: get-shared
      summary: Get shared voices
      description: Retrieves a list of shared voices.
      tags:
        - - subpackage_voices
      parameters:
        - name: page_size
          in: query
          description: >-
            How many shared voices to return at maximum. Can not exceed 100,
            defaults to 30.
          required: false
          schema:
            type: integer
        - name: category
          in: query
          description: Voice category used for filtering
          required: false
          schema:
            $ref: '#/components/schemas/V1SharedVoicesGetParametersCategory'
        - name: gender
          in: query
          description: Gender used for filtering
          required: false
          schema:
            type:
              - string
              - 'null'
        - name: age
          in: query
          description: Age used for filtering
          required: false
          schema:
            type:
              - string
              - 'null'
        - name: accent
          in: query
          description: Accent used for filtering
          required: false
          schema:
            type:
              - string
              - 'null'
        - name: language
          in: query
          description: Language used for filtering
          required: false
          schema:
            type:
              - string
              - 'null'
        - name: locale
          in: query
          description: Locale used for filtering
          required: false
          schema:
            type:
              - string
              - 'null'
        - name: search
          in: query
          description: Search term used for filtering
          required: false
          schema:
            type:
              - string
              - 'null'
        - name: use_cases
          in: query
          description: Use-case used for filtering
          required: false
          schema:
            type:
              - array
              - 'null'
            items:
              type: string
        - name: descriptives
          in: query
          description: Search term used for filtering
          required: false
          schema:
            type:
              - array
              - 'null'
            items:
              type: string
        - name: featured
          in: query
          description: Filter featured voices
          required: false
          schema:
            type: boolean
        - name: min_notice_period_days
          in: query
          description: >-
            Filter voices with a minimum notice period of the given number of
            days.
          required: false
          schema:
            type:
              - integer
              - 'null'
        - name: include_custom_rates
          in: query
          description: Include/exclude voices with custom rates
          required: false
          schema:
            type:
              - boolean
              - 'null'
        - name: include_live_moderated
          in: query
          description: Include/exclude voices that are live moderated
          required: false
          schema:
            type:
              - boolean
              - 'null'
        - name: reader_app_enabled
          in: query
          description: Filter voices that are enabled for the reader app
          required: false
          schema:
            type: boolean
        - name: owner_id
          in: query
          description: Filter voices by public owner ID
          required: false
          schema:
            type:
              - string
              - 'null'
        - name: sort
          in: query
          description: Sort criteria
          required: false
          schema:
            type:
              - string
              - 'null'
        - name: page
          in: query
          required: false
          schema:
            type: integer
        - name: xi-api-key
          in: header
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Successful Response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/GetLibraryVoicesResponseModel'
        '422':
          description: Validation Error
          content: {}
components:
  schemas:
    V1SharedVoicesGetParametersCategory:
      type: string
      enum:
        - value: professional
        - value: famous
        - value: high_quality
    LibraryVoiceResponseModelCategory:
      type: string
      enum:
        - value: generated
        - value: cloned
        - value: premade
        - value: professional
        - value: famous
        - value: high_quality
    VerifiedVoiceLanguageResponseModel:
      type: object
      properties:
        language:
          type: string
        model_id:
          type: string
        accent:
          type:
            - string
            - 'null'
        locale:
          type:
            - string
            - 'null'
        preview_url:
          type:
            - string
            - 'null'
      required:
        - language
        - model_id
    LibraryVoiceResponseModel:
      type: object
      properties:
        public_owner_id:
          type: string
        voice_id:
          type: string
        date_unix:
          type: integer
        name:
          type: string
        accent:
          type: string
        gender:
          type: string
        age:
          type: string
        descriptive:
          type: string
        use_case:
          type: string
        category:
          $ref: '#/components/schemas/LibraryVoiceResponseModelCategory'
        language:
          type:
            - string
            - 'null'
        locale:
          type:
            - string
            - 'null'
        description:
          type:
            - string
            - 'null'
        preview_url:
          type:
            - string
            - 'null'
        usage_character_count_1y:
          type: integer
        usage_character_count_7d:
          type: integer
        play_api_usage_character_count_1y:
          type: integer
        cloned_by_count:
          type: integer
        rate:
          type:
            - number
            - 'null'
          format: double
        fiat_rate:
          type:
            - number
            - 'null'
          format: double
        free_users_allowed:
          type: boolean
        live_moderation_enabled:
          type: boolean
        featured:
          type: boolean
        verified_languages:
          type:
            - array
            - 'null'
          items:
            $ref: '#/components/schemas/VerifiedVoiceLanguageResponseModel'
        notice_period:
          type:
            - integer
            - 'null'
        instagram_username:
          type:
            - string
            - 'null'
        twitter_username:
          type:
            - string
            - 'null'
        youtube_username:
          type:
            - string
            - 'null'
        tiktok_username:
          type:
            - string
            - 'null'
        image_url:
          type:
            - string
            - 'null'
        is_added_by_user:
          type:
            - boolean
            - 'null'
      required:
        - public_owner_id
        - voice_id
        - date_unix
        - name
        - accent
        - gender
        - age
        - descriptive
        - use_case
        - category
        - usage_character_count_1y
        - usage_character_count_7d
        - play_api_usage_character_count_1y
        - cloned_by_count
        - free_users_allowed
        - live_moderation_enabled
        - featured
    GetLibraryVoicesResponseModel:
      type: object
      properties:
        voices:
          type: array
          items:
            $ref: '#/components/schemas/LibraryVoiceResponseModel'
        has_more:
          type: boolean
        last_sort_id:
          type:
            - string
            - 'null'
      required:
        - voices
        - has_more

```

## SDK Code Examples

```typescript
import { ElevenLabsClient } from "@elevenlabs/elevenlabs-js";

async function main() {
    const client = new ElevenLabsClient({
        environment: "https://api.elevenlabs.io",
    });
    await client.voices.getShared({});
}
main();

```

```python
from elevenlabs import ElevenLabs

client = ElevenLabs(
    base_url="https://api.elevenlabs.io"
)

client.voices.get_shared()

```

```go
package main

import (
	"fmt"
	"net/http"
	"io"
)

func main() {

	url := "https://api.elevenlabs.io/v1/shared-voices"

	req, _ := http.NewRequest("GET", url, nil)

	req.Header.Add("xi-api-key", "xi-api-key")

	res, _ := http.DefaultClient.Do(req)

	defer res.Body.Close()
	body, _ := io.ReadAll(res.Body)

	fmt.Println(res)
	fmt.Println(string(body))

}
```

```ruby
require 'uri'
require 'net/http'

url = URI("https://api.elevenlabs.io/v1/shared-voices")

http = Net::HTTP.new(url.host, url.port)
http.use_ssl = true

request = Net::HTTP::Get.new(url)
request["xi-api-key"] = 'xi-api-key'

response = http.request(request)
puts response.read_body
```

```java
HttpResponse<String> response = Unirest.get("https://api.elevenlabs.io/v1/shared-voices")
  .header("xi-api-key", "xi-api-key")
  .asString();
```

```php
<?php

$client = new \GuzzleHttp\Client();

$response = $client->request('GET', 'https://api.elevenlabs.io/v1/shared-voices', [
  'headers' => [
    'xi-api-key' => 'xi-api-key',
  ],
]);

echo $response->getBody();
```

```csharp
var client = new RestClient("https://api.elevenlabs.io/v1/shared-voices");
var request = new RestRequest(Method.GET);
request.AddHeader("xi-api-key", "xi-api-key");
IRestResponse response = client.Execute(request);
```

```swift
import Foundation

let headers = ["xi-api-key": "xi-api-key"]

let request = NSMutableURLRequest(url: NSURL(string: "https://api.elevenlabs.io/v1/shared-voices")! as URL,
                                        cachePolicy: .useProtocolCachePolicy,
                                    timeoutInterval: 10.0)
request.httpMethod = "GET"
request.allHTTPHeaderFields = headers

let session = URLSession.shared
let dataTask = session.dataTask(with: request as URLRequest, completionHandler: { (data, response, error) -> Void in
  if (error != nil) {
    print(error as Any)
  } else {
    let httpResponse = response as? HTTPURLResponse
    print(httpResponse)
  }
})

dataTask.resume()
```