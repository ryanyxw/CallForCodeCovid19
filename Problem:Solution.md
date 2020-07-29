1. Submission name

2. The project or team name for your solution in less than five words

3. Short description

4. Describe your team’s solution in about ten words

5. 3 minute or shorter video

6. Long description

7. About 500 words, or around one page of text, that covers the solution in more detail. Please include the real-world problem you identified, describe the technology project you created, and explain why it's better than any existing solution.

# Problem:

The current COVID-19 pandemic is spreading around the world and it is very difficult to trace back the chain of infection. Further, people prefer their private and identifying information remains private and anonymous, thus hindering the contact tracing efforts. The shortage of contact tracing leads to more occurrences of transmissions of the novel corona-virus, because people do not know that they’ve been in close contact with people who contacted the novel coronavirus. This makes the people less likely to get tested and self-quarantine in a timely manner. 

# What we have created

A contact tracing app that allows users to check if they’ve been close to an individual who contracted the novel coronavirus without creating privacy concerns for either party. The app is centered around maximizing data privacy for ALL users, and ensures that private identifying data is never shared outside of each users' interactions with the service. 

## Why it’s an improvement on existing solutions:

Currently, Google has rolled out a service using periodically alternating Bluetooth tags, which makes it less reliable and less secure. Firstly, it requires the user to constantly enable Bluetooth, which many users turn off to conserve their device battery, or to minimize the risks of cyber security attacks. Secondly, this requires the phone to record every tag it has transmitted and every tag it has received to Google, greatly increasing the amount of personally identifying information stored online. Our solution uses MAC addresses, which are automatically broadcasted when devices join a WiFi network. This ensures that we can assist users without adding on new requirements to users. Our service stores the MAC addresses the user has encountered locally, and only transmits the MAC address of people encountered when the user has tested positive and agrees to share such data. The MAC addresses that said user had encountered will be anonymized by the server (all information in regards to which user met another user is not retained by the server). This also allows us also to support users who's MAC address were in close proximity with a person who had tested positive for COVID-19 before they joined our service. Because WiFi connections are much more common, and because we retain less information of our users, we believe our solution in an improvement of existing services. 

## What did you do for the past 14 days?

Seriously, please try and remember exactly where you went, what time you went, and who you might have closely interacted with for the past 14 days. Of course, that may be easy if you’ve never left the house since March like I did. However, for many COVID-19 patients, this may not be an easy task. When faced with vague responses such as “I can’t remember, it was a week ago, I just needed some toilet paper” or “Oh the rally was wild, I was just screaming all the way”, hospitals and local authorities don’t have much to go on. Such a means of tracing the footsteps of the infected COVID patients to break chains of infection has been largely discarded due to either the lack of information COVID or the lack of resources and manpower authorities have. 

What our team have created to tackle this problem is a privacy-centered application that allows individuals to know if they have been in contact with COVID patients while maintaining their anonymity by using MAC addresses broadcasted upon connection to WIFI networks. 

Every device has a specific, permanent, and unique MAC address coded into its hardware. Whenever a device establishes a connection with a WIFI network, it sends its MAC address to the all the devices on the WIFI network as part of the WiFi protocol. Knowing this, our app works as follows:

1. Whenever the user’s device is connected to a WIFI network, it records all the MAC addresses of other users also on the network (presumed to people close by given the range of Wifi) to a file stored locally. 

2. If the user contracts COVID-19, he/she could send their list of collected MAC addresses to our online server, which will mark these MAC addresses as “high risk / close contact” without linking any identifying information of the sender. 

3. All users can send their own MAC addresses to the server with a secret key (to prevent impersonation). The server will compare it to its list of MAC addresses stored in its database as high risk, and reply if the user is at high risk. 

Note : For step 2, patients can always choose to not disclose, but our database structure is set up specifically to not store any information about COVID patients who are releasing their own MAC address collection to the public. 

Note: Further information on our security features, as well as our system of verifying COVID cases, can be found in annotations on our server-side python script called `server.py`. 

COVID-19 has become the greatest pandemic humans have had to face for hundreds of years. Despite months of quarantining efforts, we have begun to see a rebound in infections as many states and countries are beginning to open up. Our team hopes that with our app, we can finally put a stop to this nightmare, once and for all. 

Naturally, there are some that propose the easy solution out - just let our phones record when and where we were, as well as who we met for the past 14 days. Then the internet can work its magic and help find the high-risk individuals. Easy, right? Although this solution may actually be feasible, it neglects a basic human right – privacy. By implementing this solution, individuals are forced to choose between either giving up their privacy, meaning that every minute of their day is recorded and uploaded to the internet, and the choice of being kept in the dark about their risk status and potentially spreading the coronavirus to their loved ones. 

1. IBM Cloud service(s) or IBM System(s) used in your solution. This question is required.
   
   Cloud Foundry (To host the server endpoint), IBM Cloudant (databases)

2. Roadmap

3. A document or image that shows how mature your solution is today and how you would like to improve it in the future. This can include information on the business model, future funding needs, and a sustainability plan.
