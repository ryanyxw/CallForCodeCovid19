# CallForCodeCovid19

## Overview

Recording MAC addresses of devices connected to the same local area network as a abstracted footprint so that individuals 
know who they have met for the past 14 days. This assists in contact tracing and the fight against COVID-19. 

## Feature Listing

1. Track if user met someone who tested positive

2. Users can report that they tested positive

3. Differentiate if a user has tested positive at a participating medical facility or if the user is cloaiming to have tested positive

4. Users can mark themselves as recovered

5. Users have the right to be forgottent. All data of participating users can be deleted if they wish to do so. 

## Functions

1. Contact tracing via collection of MAC addresses broadcasted on local network. 

2. Differentiation of risks (allegedly tested positive VS confirmed to have tested positive) when alerting users that they had met someone who tested positive

3. Able to support users who did not join our services before they met someone who tested positive

## Difference from other services

Anonymous. MAC addresses are impossible (as of now) to trace back to specific individuals without the resources of a 
government (NSA traffic correleation attack, subpoena the Internet Service Providers). Servers store the minimal amount 
of data possible, so no private information of our users will be leaked upon attackers breaching our services. 

## Security

1. We fully validate the identity of users on the server before processing their requests. 

2. Our users are authenticated by 52 character long randomized secret key. 

3. Robust blocking:
  
  1. Our blocking system is designed to minimally affect our users, if at all. The application always conducts actions that are not blocked by the server.  

  2. Attackers wishing to spam us with user creation would be promptly blocked (upon 3rd request)
  
  3. Attackers wishing to spam us with key guesses will be blocked (upon 3rd request) for 15 minutes. Thus no key can be guesses in a time frame (26^52 combinations / (3combo/15 min) = 3.606 * 10 ^ 68 years)
  
  4. Attackers attempting to impersonate admins will also be blocked on 1st try. 
  
## Demo

Our Demo can be found [here](https://youtu.be/507I2lZGL7Q). Our install packages can be found on the [releases page](https://github.com/RyanTooOp/CallForCodeCovid19/releases).

![Supports Android, Linux, macOS, Windows 10. iOS supported in theory but lacking in Appple Developer license.](https://raw.githubusercontent.com/RyanTooOp/CallForCodeCovid19/master/Images/SupportedPlatforms.jpeg)

## More Source Code/Commit History

Due to an issue regarding branches, our source code was migrated from another repository (owned by @livelycarpet87). The initial commits and the initial history of our source code can be found [there](https://github.com/LivelyCarpet87/CallForCode_COVID-19_Project). 
  
## Important Notice

**Because of limitations of our Cloud Foundry Free Tier Services, the server frequently runs low on memory and may result in 500 errors**
