function make_indata(Year, Timezone, Location, Tilt, DNI, DHI, GHI, ETHI, Ta, DewPoint, Windspeed)
%Takes TMY data input and interpolates onto the 5 minute time intervals
%required for TOMCATInputs.ipynb

%In addition, creates the required columns for angles of incidence, plane
%of array incidence, elevation, projected elevation, and sky and ground
%temperatures

Time = getTime(Year,Timezone);%Time is needed for pvl_spa
[SunAzdeg, ~, ApparentSunEl]= pvl_spa(Time, Location);%Retrieves sun azimuth and sun elevation

SparseTime = (60:60:525600);% Timestamps from TMY data file
DNI2 = interp1(SparseTime,DNI,(2.5:5:525600),'linear','extrap');%DNI interpolated onto 5 minute intervals
DHI2 = interp1(SparseTime,DHI,(2.5:5:525600),'linear','extrap');%DHI interpolated onto 5 minute intervals

DP2 = interp1(SparseTime,DewPoint,(2.5:5:525600),'linear','extrap');%Dew point interpolated onto 5 minute intervals
GHI2 = interp1(SparseTime,GHI,(2.5:5:525600),'linear','extrap');%GHI interpolated onto 5 minute intervals

AOIdeg = pvl_getaoi(Tilt, 180, 90.-ApparentSunEl, SunAzdeg);%Use pvl to get beam angle of incidence

Ta2 = interp1(SparseTime,Ta,(2.5:5:525600),'linear','extrap');%Ambient temperature interpolated onto 5 minute intervals
Windspeed2 = interp1(SparseTime,Windspeed,(2.5:5:525600),'linear','extrap');%Windspeed interpolated onto 5 minute intervals

Windspeed2 = abs(Windspeed2);%Correct for negative windspeed.

SunAzdeg = interp1((1:525600),SunAzdeg,(2.5:5:525600),'linear','extrap');%Interpolate Azimuth angle onto 5 minute intervals
ApparentSunEl = interp1((1:525600),ApparentSunEl,(2.5:5:525600),'linear','extrap');%Interpolate apparent elevation angle onto 5 minute intervals
AOIdeg = interp1((1:525600),AOIdeg,(2.5:5:525600),'linear','extrap');%Interpolate angle of incidence onto 5 minute intervals

Zendeg = 90.-ApparentSunEl;%Calculate Zenith as the complement of azimuth
SunAz = SunAzdeg *pi/180;%Radians
SunEl = ApparentSunEl *pi/180;%Radians
AOI = AOIdeg*pi/180;%Radians
Elapsed = (0:300:31535700);%CHECK IF THIS IS NOT OFF BY ONE INDEX

poai_beam = DNI2.*cosd(AOIdeg);%Calculate plane of array irradiance due to the beam. Direct normal incidence derated by angle of incidence
poai_diffuse = DHI2.*(1+cosd(Tilt))/2;%Calculate plane of array irradiance from diffuse light.

poai = poai_beam + poai_diffuse;%Total poai

SunElProj = atan2(tan(SunEl),-1*cos(SunAz));%This equation was from TOMCATInputs.ipynb


K = zeros(1,length(GHI));%Clearness Index
for i = 1:length(GHI)
    if ETHI(i) == 0
            K(i) = 1;
    else
        K(i) = GHI(i)/ETHI(i);%Calculate clearness index for sky and ground temps
    end

end
K(K > 1) = 1;%Correct for errors in measurement in GHI


K2 = interp1(SparseTime,K,(2.5:5:525600),'linear','extrap');%Clearness index interpolated onto 5 minute intervals

x = [123.1415;11.3444;4.2073;0.4447];%coefficients for sky temp model, do not change unless you re-fit the model

TskyEst = SkyTempModel(x,K2,Ta2,DP2);%Need coefficients x from sky model fit for Golden
TgroundEst = Ta2 - 1.362 + 1.287*10^-2.*GHI2;%Tground correlation
for i = 1:length(poai)%Clip the data as in TOMCATInputs.ipynb. 1e-9 is the minimum value
   
    if poai(i) < 1e-9
        poai(i) = 1e-9;
    end
    if poai(i) > 2000
        poai(i) = 2000;
    end
    if poai_beam(i) < 1e-9
        poai_beam(i) = 1e-9;
    end
    if poai_beam(i) > 2000
        poai_beam(i) = 2000;
    end
    if poai_diffuse(i) < 1e-9
        poai_diffuse(i) = 1e-9;
    end
    if poai_diffuse(i) > 2000
        poai_diffuse(i) = 2000;
    end
    if DNI2(i) < 1e-9
        DNI2(i) = 1e-9;
    end
    if DNI2(i) > 2000
        DNI2(i) = 2000;
    end
    if SunElProj(i) < 0
        SunElProj(i) = 0;
    end
    if SunElProj(i) > pi
        SunElProj(i) = pi;
    end
    if SunEl(i) < 0
        SunEl(i) = 0;
    end
    if SunEl(i) > pi
        SunEl(i) = pi;
    end
end

headers = {'wind_speed','poai','dni','temp','zenith_deg','azimuth_deg','aoi_deg','aoi','elevation','azimuth','elevation_projected','elapsed','poai_beam','poai_diffuse','temp_sky','temp_ground'};

%Write to csv with headers
if ~isequal(length(Windspeed2),length(poai),length(DNI2),length(Ta2),length(Zendeg),length(SunAzdeg),length(AOIdeg),length(AOI),length(SunEl),length(SunAz),length(SunElProj),length(Elapsed),length(poai_beam),length(poai_diffuse),length(TskyEst),length(TgroundEst))
    error('make_indata: input vectors not of equal length\n');
end

m = [Windspeed2;poai;DNI2;Ta2+273.15;Zendeg;SunAzdeg;AOIdeg;AOI;SunEl;SunAz;SunElProj;Elapsed;poai_beam;poai_diffuse;TskyEst;TgroundEst+273.15];
%m is a big matrix with all data
%disp(size(m));
%disp(size(headers));
csvwrite_with_headers('indata.csv',m',headers,0,0);
end