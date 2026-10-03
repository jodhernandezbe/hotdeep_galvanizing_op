
%% GREENSCOPE to calculate the 17 indicators which were selected
% For: Jose Daniel Hernandez Betancur
% Mater thesis title: "Detection of the critcal points of hot-dip galvanizing process:
% a focus on sustainability and sustainable development
% Master degree's name: Master in Engineering - Materials and Processes
% University: National University of Colombia - Medellin branch
% Date: 12 December, 2017
%%-----------------------------------------------------------------------------------------------------------

function [G_I,G_score] = greenscope(Input_streams,Output_streams,EC,MW_sodium_carboxylate,MW_grease,...
m_Fe2_1,m_Fe2_2,m_surface_area_T)

%%-----------------------------------------------------------------------------------------------------------
%%-----------------------------------------------------------------------------------------------------------
%
% Compounds:
%
% (1) Steel
% (2) Triglyceride
% (3) Wustite
% (4) Sodium Hydroxide
% (5) Water
% (6) Glycerol
% (7) Sodium Carboxylates
% (8) Hydrochloric Acid
% (9) Iron Dichloride
% (10) Zinc
% (11) Zinc Dichloride
% (12) Ammonium Chloride
% (13) Ammonium Hydroxide
% (14) Zinc Hydroxide
% (15) Ferrous Hydroxide
% (16) Dross
% (17) Ash
%
%------------------------------------------------------------------------------------------------------------
%------------------------------------------------------------------------------------------------------------

%% INPUTS:

% % % %Input streams clasification: Is the stream considered renewable?
% Input_renewable = {'NO','NO','NO','NO','NO','NO','NO','NO','NO',...
% 'NO','NO','NO'};
%
% % % OUTPUTS:
%
% % % %Output streams clasification: Is the stream considered a product?
% Output_waste = {'NO','NO','NO','NO','NO','NO','NO','NO','NO','YES'};
%
% % % %Output streams clasification: Is the stream considered a polluted waste?
% Output_polluted = {'YES','YES','YES','YES','YES','YES','YES','YES','YES','NA'};
%
% % % %Output streams clasification: Is the stream considered a renewable
% % % %product?
% Output_renewable = {'NA','NA','NA','NA','NA','NA','NA','NA','NA','NO'};
%
% % % %Output streams clasification: Is the stream considered a hazardous waste?
% Output_hazardous = {'YES','YES','NO','YES','NO','YES','NO','NO','NO','NA'};
%


EC_class = {'NA','NA','NA','C','NA','NA','NA','C','C','Xn','Xn','Xn','Xn','Xn','NA','NA','NA'};
R_code = {'NA','NA','NA',35,'NA','NA','NA',34,34,20,22,22,22,22,22,'NA','NA'};
GK = {'NA','NA','NA',2,'NA','NA','NA',2,'NA','NA','NA','NA','NA','NA','NA','NA','NA'};
GWK = {'NA','NA','NA','NA','NA','NA','NA',1,'NA','NA','NA','NA','NA','NA','NA','NA','NA'};
IDLH = {1e5,'NA',2500,10,'NA','NA','NA',74.56,'NA','NA','NA','NA',208.96,'NA','NA',1e5,1e5}; % mg/m3
ERPG_3 = {'NA','NA','NA',50,'NA','NA','NA',223.68,'NA','NA','NA','NA',1044.79,'NA','NA','NA','NA'}; % mg/m3
LC_50 = {1e3,1e4,50000,160,1e4,5000,1e4,20.5,3.124,5.100,'NA','NA',8.2,'NA',1e5,1e3,1e3}; % mg/L
MAK_CH = {1e4,1e4,10,2,'NA',1e4,1e4,3,'NA',5,'NA','NA',14,'NA',10,1e4,1e4}; % mg/m3
PF_CO2 = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]; % kgCO2/kg
PF_SO2 = [0,0,0,0,0,0,0,0.88,0,0,0,0,1.88,0,0,0,0]; % kgSO2/kg
PF_ethylene = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]; % kg_ethylene/kg
PF_natural_gas = 25; % kgCO2/kg
PF_hydroelectric = 4; % kgCO2/kWh

PhysVal = SH(EC_class,R_code,GK,IDLH,ERPG_3,LC_50,MAK_CH,GWK);

G_I = zeros(7,17);
G_I_best = zeros(7,17);
G_I_worst = zeros(7,17);
G_score = zeros(7,17);

%% (1) GREENSCOPE indicators:

%% Environment

% (1) Acute Toxicity

G_I(1,1) = (dot(sum(Input_streams(1:3,:)),PhysVal(:,1)') + ...
dot(Output_streams(1,6:7),PhysVal(6:7,1)'))/sum(Output_streams(10,:));
G_I(2,1) = (dot(Input_streams(4,:),PhysVal(:,1)') + ...
dot(Output_streams(3,1:4),PhysVal(1:4,1)') + ...
dot(Output_streams(3,6:17),PhysVal(6:17,1)'))/sum(Output_streams(10,:));
G_I(3,1) = (dot(sum(Input_streams(5:6,:)),PhysVal(:,1)') + ...
dot(Output_streams(4,1:4),PhysVal(1:4,1)') + ...
dot(Output_streams(4,6:7),PhysVal(6:7,1)') + ...
dot(Output_streams(4,9:17),PhysVal(9:17,1)'))/sum(Output_streams(10,:));
G_I(4,1) = (dot(Input_streams(7,:),PhysVal(:,1)') + ...
dot(Output_streams(5,1:4),PhysVal(1:4,1)') + ...
dot(Output_streams(5,6:17),PhysVal(6:17,1)'))/sum(Output_streams(10,:));
G_I(5,1) = (dot(sum(Input_streams(8:11,:)),PhysVal(:,1)') + ...
dot(sum(Output_streams(6:7,1:4)),PhysVal(1:4,1)') + ...
dot(sum(Output_streams(6:7,6:7)),PhysVal(6:7,1)') + ...
dot(sum(Output_streams(6:7,9:10)),PhysVal(9:10,1)') + ...
dot(sum(Output_streams(6:7,14:17)),PhysVal(14:17,1)'))/sum(Output_streams(10,:));
G_I(6,1) = 0;
G_I(7,1) = (dot(Input_streams(12,:),PhysVal(:,1)') + ...
dot(sum(Output_streams(8:9,:)),PhysVal(:,1)'))/sum(Output_streams(10,:));

% (2) Air Hazard

G_I(1,2) = (dot(sum(Input_streams(1:3,:)),PhysVal(:,2)') + ...
dot(Output_streams(1,6:7),PhysVal(6:7,2)'))/sum(Output_streams(10,:));
G_I(2,2) = (dot(Input_streams(4,:),PhysVal(:,2)') + ...
dot(Output_streams(3,1:4),PhysVal(1:4,2)') + ...
dot(Output_streams(3,6:17),PhysVal(6:17,2)'))/sum(Output_streams(10,:));
G_I(3,2) = (dot(sum(Input_streams(5:6,:)),PhysVal(:,2)') + ...
dot(Output_streams(4,1:4),PhysVal(1:4,2)') + ...
dot(Output_streams(4,6:7),PhysVal(6:7,2)') + ...
dot(Output_streams(4,9:17),PhysVal(9:17,2)'))/sum(Output_streams(10,:));
G_I(4,2) = (dot(Input_streams(7,:),PhysVal(:,2)') + ...
dot(Output_streams(5,1:4),PhysVal(1:4,2)') + ...
dot(Output_streams(5,6:17),PhysVal(6:17,2)'))/sum(Output_streams(10,:));
G_I(5,2) = (dot(sum(Input_streams(8:11,:)),PhysVal(:,2)') + ...
dot(sum(Output_streams(6:7,1:4)),PhysVal(1:4,2)') + ...
dot(sum(Output_streams(6:7,6:7)),PhysVal(6:7,2)') + ...
dot(sum(Output_streams(6:7,9:10)),PhysVal(9:10,2)') + ...
dot(sum(Output_streams(6:7,14:17)),PhysVal(14:17,2)'))/sum(Output_streams(10,:));
G_I(6,2) = 0;
G_I(7,2) = (dot(Input_streams(12,:),PhysVal(:,2)') + ...
dot(sum(Output_streams(8:9,:)),PhysVal(:,2)'))/sum(Output_streams(10,:));

% (3) Water Hazard

G_I(1,3) = dot(sum(Output_streams(1:2,:)),PhysVal(:,3)')/sum(Output_streams(10,:));
G_I(2,3) = dot(Output_streams(3,:),PhysVal(:,3)')/sum(Output_streams(10,:));
G_I(3,3) = dot(Output_streams(4,:),PhysVal(:,3)')/sum(Output_streams(10,:));
G_I(4,3) = dot(Output_streams(5,:),PhysVal(:,3)')/sum(Output_streams(10,:));
G_I(5,3) = dot(sum(Output_streams(6:7,:)),PhysVal(:,3)')/sum(Output_streams(10,:));
G_I(6,3) = 0;
G_I(7,3) = dot(sum(Output_streams(8:9,:)),PhysVal(:,3)')/sum(Output_streams(10,:));

% (4) Global Warming Potential

G_I(1,4) = (dot(sum(Output_streams(1:2,:)),PF_CO2) + ...
EC(1)*(PF_natural_gas*1e-6/1.99714))/sum(Output_streams(10,:));
G_I(2,4) = dot(Output_streams(3,:),PF_CO2)/sum(Output_streams(10,:));
G_I(3,4) = dot(Output_streams(4,:),PF_CO2)/sum(Output_streams(10,:));
G_I(4,4) = dot(Output_streams(5,:),PF_CO2)/sum(Output_streams(10,:));
G_I(5,4) = (dot(sum(Output_streams(6:7,:)),PF_CO2) + ...
EC(5)*(PF_natural_gas*1e-6/1.99714))/sum(Output_streams(10,:));
G_I(6,4) = PF_hydroelectric*EC(6)*2.78e-7/sum(Output_streams(10,:));
G_I(7,4) = (dot(sum(Output_streams(8:9,:)),PF_CO2) + ...
EC(7)*(PF_natural_gas*1e-6/1.99714))/sum(Output_streams(10,:));

% (5) Photochemical Oxidation Potential

G_I(1,5) = dot(sum(Output_streams(1:2,:)),PF_ethylene)/sum(Output_streams(10,:));
G_I(2,5) = dot(Output_streams(3,:),PF_ethylene)/sum(Output_streams(10,:));
G_I(3,5) = dot(Output_streams(4,:),PF_ethylene)/sum(Output_streams(10,:));
G_I(4,5) = dot(Output_streams(5,:),PF_ethylene)/sum(Output_streams(10,:));
G_I(5,5) = dot(sum(Output_streams(6:7,:)),PF_ethylene)/sum(Output_streams(10,:));
G_I(6,5) = 0;
G_I(7,5) = dot(sum(Output_streams(8:9,:)),PF_ethylene)/sum(Output_streams(10,:));

% (6) Atmospheric Acidification Potential

G_I(1,5) = dot(sum(Output_streams(1:2,:)),PF_SO2)/sum(Output_streams(10,:));
G_I(2,5) = dot(Output_streams(3,:),PF_SO2)/sum(Output_streams(10,:));
G_I(3,5) = dot(Output_streams(4,:),PF_SO2)/sum(Output_streams(10,:));
G_I(4,5) = dot(Output_streams(5,:),PF_SO2)/sum(Output_streams(10,:));
G_I(5,5) = dot(sum(Output_streams(6:7,:)),PF_SO2)/sum(Output_streams(10,:));
G_I(6,5) = 0;
G_I(7,5) = dot(sum(Output_streams(8:9,:)),PF_SO2)/sum(Output_streams(10,:));

% (7) Polluted Liquid Waste Volume

% 60 % of NaOH is recovered
% 40 % of H2O is recovered
% 55 % of HCl is recovered

C= 0.4*Output_streams(1,4)*100/(sum(Output_streams(1,:)) - 0.6*Output_streams(1,4));
rhoNaOH1 = density(25,C,1);
G_I(1,7) = (sum(Output_streams(1,:)) - 0.6*Output_streams(1,4))/rhoNaOH1;

G_I(2,7) = 0;

C = 0.45*Output_streams(4,8)*100/(sum(Output_streams(4,:)) - 0.55*Output_streams(4,8));
rhoHCl1 = density(25,C,2);
G_I(3,7) = (sum(Output_streams(4,:)) - 0.55*Output_streams(4,8))/rhoHCl1;

G_I(4,7) = 0;
G_I(5,7) = sum(Output_streams(6,:))/1030;
G_I(6,7) = 0;
G_I(7,7) = 0;

% (8) Specific Hazardous Solid Waste

G_I(1,8) = Output_streams(2,2)/sum(Output_streams(10,:));
G_I(2,8) = 0;
G_I(3,8) = 0;
G_I(4,8) = 0;
G_I(5,8) = 0;
G_I(6,8) = 0;
G_I(7,8) = 0;

% (9) Specific Solid Waste Mass

G_I(1,9) = Output_streams(2,2)/sum(Output_streams(10,:));
G_I(2,9) = 0;
G_I(3,9) = 0;
G_I(4,9) = 0;
G_I(5,9) = sum(Output_streams(7,:))/sum(Output_streams(10,:));
G_I(6,9) = 0;
G_I(7,9) = (Output_streams(8,16) + Output_streams(9,17))/...
sum(Output_streams(10,:));

% (10) Specific Liquid Waste Volume

G_I(1,10) = (sum(Output_streams(1,:)) - 0.6*Output_streams(1,4))...
/(sum(Output_streams(10,:))*rhoNaOH1);
G_I(2,10) = (sum(Output_streams(3,:)) - 0.4*Output_streams(3,5))...
/(sum(Output_streams(10,:))*1000);
G_I(3,10) = (sum(Output_streams(4,:)) - 0.55*Output_streams(4,8))...
/(sum(Output_streams(10,:))*rhoHCl1);
G_I(4,10) = (sum(Output_streams(5,:)) - 0.4*Output_streams(5,5))...
/(sum(Output_streams(10,:))*1000);
G_I(5,10) = sum(Output_streams(6,:))/(sum(Output_streams(10,:))*1030);
G_I(6,10) = 0;
G_I(7,10) = 0;

% (11) Recycling Mass Fraction

G_I(1,11) = 0;
G_I(2,11) = 1;
G_I(3,11) = 1;
G_I(4,11) = 1;
G_I(5,11) = 0;
G_I(6,11) = 1;
G_I(7,11) = 0;

%% Material Efficiency

% (12) Actual Atom Economy

G_I(1,12) = MW_sodium_carboxylate*Output_streams(1,7)/...
((MW_grease + 3*39.9971)*(Input_streams(1,2)/MW_grease)*MW_sodium_carboxylate);
G_I(2,12) = 1;

G_I(3,12) = 55.845*m_Fe2_1/((71.8444 + 2*36.4609)*(0.8825*Input_streams(1,3)*55.845/71.8444));
G_I(4,12) = 1;
G_I(5,12) = 55.845*m_Fe2_2/((71.8444 + 2*1.0079)*(0.1175*Input_streams(1,3)*55.845/71.8444));
G_I(6,12) = 1;

% 3Fe + 10Zn -> Fe3Zn10
G_I(7,12) = 821.6250*Output_streams(10,10)/((3*55.845 + 10*65.409)*m_surface_area_T*821.6250/(3*55.845));

% (13) Environmental Factor
G_I(1,13) = (sum(sum(Output_streams(1:2,1:4))) + sum(sum(Output_streams(1:2,6:17))))/...
sum(Output_streams(10,:));
G_I(2,13) = (sum(Output_streams(3,1:4)) + sum(Output_streams(3,6:17)))/...
sum(Output_streams(10,:));
G_I(3,13) = (sum(Output_streams(4,1:4)) + sum(Output_streams(4,6:17)))/...
sum(Output_streams(10,:));
G_I(4,13) = (sum(Output_streams(5,1:4)) + sum(Output_streams(5,6:17)))/...
sum(Output_streams(10,:));
G_I(5,13) = (sum(sum(Output_streams(6:7,1:4))) + sum(sum(Output_streams(6:7,6:17))))/...
sum(Output_streams(10,:));
G_I(6,13) = 0;
G_I(7,13) = (sum(sum(Output_streams(8:9,1:4))) + sum(sum(Output_streams(8:9,6:17))))/...
sum(Output_streams(10,:));

% (14) Recycled Material Fraction (Feedstocks)

G_I(1,14) = 0.6*Output_streams(1,4)/sum(sum(Input_streams(1:3,2:17)));
G_I(2,14) = 0.4*Output_streams(3,5)/Input_streams(4,5);
G_I(3,14) = 0.55*Output_streams(4,8)/sum(sum(Input_streams(5:6,2:17)));
G_I(4,14) = 0.4*Output_streams(5,5)/Input_streams(7,5);
G_I(5,14) = 0;
G_I(6,14) = 1;
G_I(7,14) = 0;

% (15) Total Water Consumption

G_I(1,15) = sum(Input_streams(2:3,5))/1000;
G_I(2,15) = (Input_streams(4,5) - 0.4*Output_streams(3,5))/1000;
G_I(3,15) = sum(Input_streams(5:6,5))/1000;
G_I(4,15) = (Input_streams(7,5) - 0.4*Output_streams(5,5))/1000;
G_I(5,15) = sum(Input_streams(9:11,5))/1000;
G_I(6,15) = 0;
G_I(7,15) = 0;

%% Energy

% (16) Specific Energy Intensity

G_I(1,16) = (2.5512/1.99714)*EC(1)*1e-6/sum(Output_streams(10,:));
G_I(2,16) = 0;
G_I(3,16) = 0;
G_I(4,16) = 0;
G_I(5,16) = (2.5512/1.99714)*EC(5)*1e-6/sum(Output_streams(10,:));
G_I(6,16) = (10.3/3.6)*EC(6)*1e-6/sum(Output_streams(10,:));
G_I(7,16) = EC(7)*1e-6/sum(Output_streams(10,:));

%% Economy

% (17) Manufacturing Cost

%% % Raw Material Cost
% https://www.kemcore.com, https://www.alibaba.com http://en.wiegel.de/zinc-price/
% http://www.ebay.com
% (1) NaOH 50 % wt 580 USD/ton
% (2) HCl 37 % wt 165.5 USD/ton
% (3) NH4Cl 150 USD/ton
% (4) ZnCl2 990 USD/ton
% (5) Zn 99.9 % wt 2590 USD/ton
% (6) H2O 0.7755 USD/ton
% (7) NH4OH 30 % 2.1L, 257000 COP (0.9g/cm3)

RMC = [580 165.5 150 990 2590 0.7755 38.11];

CRM(1) = (RMC(1)*sum(Input_streams(2,:)) + RMC(6)*Input_streams(3,5))*1e-3;
CRM(2) = RMC(6)*Input_streams(4,5)*1e-3;
CRM(3) = (RMC(2)*sum(Input_streams(5,:)) + RMC(6)*Input_streams(6,5))*1e-3;
CRM(4) = RMC(6)*Input_streams(7,5)*1e-3;
CRM(5) = (RMC(4)*Input_streams(8,11) + RMC(3)*Input_streams(8,12)...
+ RMC(6)*Input_streams(9,5) + RMC(2)*sum(Input_streams(11,:))...
+ RMC(7)*sum(Input_streams(10,:)))*1e-3;
CRM(6) = 0;
CRM(7) = RMC(5)*Input_streams(12,10)*1-3;

% Utility Cost

CUT(1) = 0.45*EC(1)*2.78e-7/(15.75*0.737);
CUT(2) = 0;
CUT(3) = 0;
CUT(4) = 0;
CUT(5) = 0.45*EC(5)*2.78e-7/(15.75*0.737);
CUT(6) = 0.17*EC(6)*2.78e-7;
CUT(7) = 0.45*EC(7)*2.78e-7/(15.75*0.737);

% Waste treatment cost

CWT(1) = RMC(6)*1*Output_streams(1,4)/2100 + 0.17*10*Output_streams(1,4)/2100;
CWT(2) = 0.001192*sum(Output_streams(3,:))*264/1000;
CWT(3) = RMC(6)*1*Output_streams(4,8)/1190 + 0.17*10*Output_streams(4,8)/1190;
CWT(4) = 0.001192*sum(Output_streams(5,:))*264/1000;
CWT(5) = 0;
CWT(6) = 0;
CWT(7) = 0;

% Labor cost

% Hot-dip galvanizing plant has 8 operators:
% Pre-treatment: 2
% Galvanizing: 2
% Bridge crane: 2
% Post-treatment: 2

COL = 4.5*4135.89*2*ones(1,7);

% Fixed Capital Investment

FCI(1) = 80920 + 184275;
FCI(2) = 80920;
FCI(3) = 80920*2 + 184275;
FCI(4) = 80920;
FCI(5) = 80920;
FCI(6) = 60690;
FCI(7) = 1000000;

G_I(1:7,17) = 0.280.*FCI' + 2.73.*COL' + 1.23.*(CRM' + CUT' + CWT');

%% %----------------------------------------------------------------------------------------------------------
%% %----------------------------------------------------------------------------------------------------------

%% (2) GREENSCOPE the worst and best cases:

%% Environment

% (1) Acute Toxicity

G_I_worst(:,1) = 1e5*ones(7,1);

% (2) Air Hazard

G_I_worst(:,2) = 1e7*ones(7,1);

% (3) Water Hazard

G_I_worst(:,3) = 1e5*ones(7,1);

% (4) Global Warming Potential

PF_CO2_worst = PF_CO2;

for j = 1:17

if PF_CO2_worst(j) == 0

PF_CO2_worst(j) = 1;

end

end

clear j

G_I_worst(1,4) = (dot(sum(Output_streams(1:2,:)),PF_CO2_worst) + ...
EC(1)*(PF_natural_gas*1e-6/1.99714))/sum(Output_streams(10,:));
G_I_worst(2,4) = dot(Output_streams(3,:),PF_CO2_worst)/sum(Output_streams(10,:));
G_I_worst(3,4) = dot(Output_streams(4,:),PF_CO2_worst)/sum(Output_streams(10,:));
G_I_worst(4,4) = dot(Output_streams(5,:),PF_CO2_worst)/sum(Output_streams(10,:));
G_I_worst(5,4) = (dot(sum(Output_streams(6:7,:)),PF_CO2_worst) + ...
EC(5)*(PF_natural_gas*1e-6/1.99714))/sum(Output_streams(10,:));
G_I_worst(6,4) = PF_hydroelectric*EC(6)*2.78e-7/sum(Output_streams(10,:));
G_I_worst(7,4) = (dot(sum(Output_streams(8:9,:)),PF_CO2_worst) + ...
EC(7)*(PF_natural_gas*1e-6/1.99714))/sum(Output_streams(10,:));

% (5) Photochemical Oxidation Potential

PF_ethylene_worst = PF_ethylene;

for j = 1:17

if PF_ethylene_worst(j) == 0

PF_ethylene_worst(j) = 1;

end

end

clear j

G_I_worst(1,5) = dot(sum(Output_streams(1:2,:)),PF_ethylene_worst)/sum(Output_streams(10,:));
G_I_worst(2,5) = dot(Output_streams(3,:),PF_ethylene_worst)/sum(Output_streams(10,:));
G_I_worst(3,5) = dot(Output_streams(4,:),PF_ethylene_worst)/sum(Output_streams(10,:));
G_I_worst(4,5) = dot(Output_streams(5,:),PF_ethylene_worst)/sum(Output_streams(10,:));
G_I_worst(5,5) = dot(sum(Output_streams(6:7,:)),PF_ethylene_worst)/sum(Output_streams(10,:));
G_I_worst(6,5) = 1;
G_I_worst(7,5) = dot(sum(Output_streams(8:9,:)),PF_ethylene_worst)/sum(Output_streams(10,:));

% (6) Atmospheric Acidification Potential

PF_SO2_worst = PF_SO2;

for j = 1:17

if PF_SO2_worst(j) == 0

PF_SO2_worst(j) = 1;

end

end

clear j

G_I_worst(1,6) = dot(sum(Output_streams(1:2,:)),PF_SO2_worst)/sum(Output_streams(10,:));
G_I_worst(2,6) = dot(Output_streams(3,:),PF_SO2_worst)/sum(Output_streams(10,:));
G_I_worst(3,6) = dot(Output_streams(4,:),PF_SO2_worst)/sum(Output_streams(10,:));
G_I_worst(4,6) = dot(Output_streams(5,:),PF_SO2_worst)/sum(Output_streams(10,:));
G_I_worst(5,6) = dot(sum(Output_streams(6:7,:)),PF_SO2_worst)/sum(Output_streams(10,:));
G_I_worst(6,6) = 1;
G_I_worst(7,6) = dot(sum(Output_streams(8:9,:)),PF_SO2_worst)/sum(Output_streams(10,:));

% (7) Polluted Liquid Waste Volume

C= Output_streams(1,4)*100/sum(Output_streams(1,4:5));
rhoNaOH1 = density(25,C,1);
G_I_worst(1,7) = sum(Output_streams(1,:))/rhoNaOH1;

G_I_worst(2,7) = 1;

C = Output_streams(4,8)*100/sum(Output_streams(4,:));
rhoHCl1 = density(25,C,2);
G_I_worst(3,7) = sum(Output_streams(4,:))/rhoHCl1;

G_I_worst(4,7) = 1;
G_I_worst(5,7) = sum(Output_streams(6,:))/1030;
G_I_worst(6,7) = 1;
G_I_worst(7,7) = 1;

% (8) Specific Hazardous Solid Waste

G_I_worst(1,8) = Output_streams(2,2)/sum(Output_streams(10,:));
G_I_worst(2,8) = 1;
G_I_worst(3,8) = 1;
G_I_worst(4,8) = 1;
G_I_worst(5,8) = 1;
G_I_worst(6,8) = 1;
G_I_worst(7,8) = 1;

% (9) Specific Solid Waste Mass

G_I_worst(1,9) = Output_streams(2,2)/sum(Output_streams(10,:));
G_I_worst(2,9) = 1;
G_I_worst(3,9) = 1;
G_I_worst(4,9) = 1;
G_I_worst(5,9) = sum(Output_streams(7,:))/sum(Output_streams(10,:));
G_I_worst(6,9) = 1;
G_I_worst(7,9) = (Output_streams(8,16) + Output_streams(9,17))/...
sum(Output_streams(10,:));

% (10) Specific Liquid Waste Volume

G_I_worst(1,10) = sum(Output_streams(1,:))/(sum(Output_streams(10,:))*rhoNaOH1);
G_I_worst(2,10) = sum(Output_streams(3,:))/(sum(Output_streams(10,:))*1000);
G_I_worst(3,10) = sum(Output_streams(4,:))/(sum(Output_streams(10,:))*rhoHCl1);
G_I_worst(4,10) = sum(Output_streams(5,:))/(sum(Output_streams(10,:))*1000);
G_I_worst(5,10) = sum(Output_streams(6,:))/(sum(Output_streams(10,:))*1030);
G_I_worst(6,10) = 1;
G_I_worst(7,10) = 1;

% (11) Recycling Mass Fraction

G_I_best(:,11) = ones(7,1);


%% Material Efficiency

% (12) Actual Atom Economy

G_I_best(:,12) = ones(7,1);

% (13) Environmental Factor

G_I_worst(:,13) = 39*ones(7,1);

% (14) Recycled Material Fraction (Feedstocks)

G_I_best(:,14) = ones(7,1);

% (15) Total Water Consumption

G_I_worst(1,15) = sum(Input_streams(2:3,5))/1000;
G_I_worst(2,15) = Input_streams(4,5)/1000;
G_I_worst(3,15) = sum(Input_streams(5:6,5))/1000;
G_I_worst(4,15) = Input_streams(7,5)/1000;
G_I_worst(5,15) = sum(Input_streams(9:11,5))/1000;
G_I_worst(6,15) = 1;
G_I_worst(7,15) = 1;

%% Energy

% (16) Specific Energy Intensity
C_NaOH = Input_streams(2,4)*100/sum(sum(Input_streams(2:3,:)));
Cp_NaOH = -627.6*(C_NaOH - 1.08)/16.73 + 4121.2;
G_I_best(1,16) = (2.5512/1.99714)*sum(sum(Input_streams(2:3,:)))*Cp_NaOH*(50 - 25)...
*1e-6/sum(Output_streams(10,:));
G_I_best(2,16) = 0;
G_I_best(3,16) = 0;
G_I_best(4,16) = 0;
G_I_best(5,16) = (2.5512/1.99714)*sum(sum(Input_streams(8:11,:)))*96.232*(50 - 25)...
*1e-6/sum(Output_streams(10,:));
G_I_best(6,16) = 0.5*(10.3/3.6)*Output_streams(10,1)*450*(100 - 25)...
*1e-6/sum(Output_streams(10,:));
G_I_best(7,16) = 1e-6*Input_streams(12,10)*1000*(0.3883*(419.5 - 25) + 100.9 + 0.4801*(450 - 419.5))/...
sum(Output_streams(10,:));



G_I_worst(1,16) = 1e3*G_I_best(1,16);
G_I_worst(2,16) = 10;
G_I_worst(3,16) = 10;
G_I_worst(4,16) = 10;
G_I_worst(5,16) = 1e3*G_I_best(5,16);
G_I_worst(6,16) = 1e1*G_I_best(6,16);
G_I_worst(7,16) = 1e2*G_I_best(7,16);

%% Economy

% (17) Manufacturing Cost

% Taking general expenses (GE) as 15 % of total cost of product (TPC)
% TPC = GE + COM -> TPC = COM/0.85

G_I_best(:,17) = (0.38/0.85)*G_I(:,17);
G_I_worst(:,17) = (1.7/0.85)*G_I(:,17);

%% %----------------------------------------------------------------------------------------------------------
%% %----------------------------------------------------------------------------------------------------------

%% (3) GREENSCOPE score

for i = 1:7

for j = 1:17

G_score(i,j) = (G_I(i,j) - G_I_worst(i,j))*100/...
(G_I_best(i,j) - G_I_worst(i,j));

end

end

return

function PhysVal = SH(EC_class,R_code,GK,IDLH,ERPG_3,LC_50,MAK_CH,GWK)

PhysVal = zeros(17,3);
IndVal = zeros(17,3);

% For Acute Toxicity

for i = 1:17

% For Acute Toxicity

if (strcmp(IDLH{i},'NA') == 0) || (strcmp(ERPG_3{i},'NA') == 0)

if (strcmp(IDLH{i},'NA') == 0)

IDLH_ERPG_3 = IDLH{i};

else

IDLH_ERPG_3 = ERPG_3{i};

end

if (10 < IDLH_ERPG_3) && (IDLH_ERPG_3 < 1e5)

IndVal(i,1) = - 0.109*log(IDLH_ERPG_3) + 1.25;

elseif IDLH_ERPG_3 <= 10

IndVal(i,1) = 1;

elseif IDLH_ERPG_3 >= 1e5

IndVal(i,1) = 0;

end

elseif (strcmp(EC_class{i},'NA') == 0)

if (strcmp(EC_class{i},'T_plus') == 1)

IndVal(i,1) = 0.875;

elseif (strcmp(EC_class{i},'T') == 1)

IndVal(i,1) = 0.625;

elseif (strcmp(EC_class{i},'Xn') == 1)

IndVal(i,1) = 0.375;

end

elseif (strcmp(GK{i},'NA') == 0)

if GK{i} == 1

IndVal(i,1) = 1;

elseif GK{i} == 2

IndVal(i,1) = 0.875;

elseif GK{i} == 3

IndVal(i,1) = 0.625;

elseif GK{i} == 4

IndVal(i,1) = 0.375;

elseif GK{i} == 5

IndVal(i,1) = 0.125;

else

IndVal(i,1) = 0;

end

elseif (strcmp(R_code{i},'NA') == 0)

if (R_code{i} == 26) || (R_code{i} == 27) || (R_code{i} == 28) || ...
(R_code{i} == 29) || (R_code{i} == 32)

IndVal(i,1) = 0.875;

elseif (R_code{i} == 23) || (R_code{i} == 24) || (R_code{i} == 25) || ...
(R_code{i} == 31)

IndVal(i,1) = 0.625;

elseif (R_code{i} == 20) || (R_code{i} == 21) || (R_code{i} == 22)

IndVal(i,1) = 0.375;

end

end

if IndVal(i,1) > 0

PhysVal(i,1) = 10^(4*IndVal(i,1) + 1);

elseif IndVal(i,1) == 0;

PhysVal(i,1) = 0;

end

% For Air Hazard

if (strcmp(MAK_CH{i},'NA') == 0)

if (0.1 < MAK_CH{i}) && (MAK_CH{i} < 1e4)

IndVal(i,2) = - 0.087*log(MAK_CH{i}) + 0.8;

elseif MAK_CH{i} <= 0.1

IndVal(i,2) = 1;

elseif MAK_CH{i} >= 1e4

IndVal(i,2) = 0;

end

elseif (strcmp(EC_class{i},'NA') == 0)

if (strcmp(EC_class{i},'T_plus') == 1)

IndVal(i,2) = 0.7;

elseif (strcmp(EC_class{i},'T') == 1)

IndVal(i,2) = 0.5;

elseif (strcmp(EC_class{i},'Xn') == 1)

IndVal(i,2) = 0.3;

end

elseif (strcmp(GK{i},'NA') == 0)

if GK{i} == 1

IndVal(i,2) = 0.8;

elseif GK{i} == 2

IndVal(i,2) = 0.7;

elseif GK{i} == 3

IndVal(i,2) = 0.5;

elseif GK{i} == 4

IndVal(i,2) = 0.3;

elseif GK{i} == 5

IndVal(i,2) = 0.1;

else

IndVal(i,2) = 0;

end

elseif (strcmp(R_code{i},'NA') == 0)

if (R_code{i} == 45) || (R_code{i} == 46) || (R_code{i} == 47) || ...
(R_code{i} == 49) || (R_code{i} == 60) || (R_code{i} == 61)

IndVal(i,2) = 1;

elseif (R_code{i} == 40) || (R_code{i} == 62) || (R_code{i} == 63) || ...
(R_code{i} == 64)

IndVal(i,2) = 0.8;

elseif (R_code{i} == 29) || (R_code{i} == 32) || (R_code{i} == 64)

IndVal(i,2) = 0.7;

elseif (R_code{i} == 42) || (R_code{i} == 43)

IndVal(i,2) = 0.6;

elseif (R_code{i} == 31) || (R_code{i} == 33)

IndVal(i,2) = 0.5;

else

IndVal(i,2) = 0;

end

end

if IndVal(i,2) > 0

PhysVal(i,2) = 10^(5*IndVal(i,2) + 2);

elseif IndVal(i,2) == 0;

PhysVal(i,2) = 0;

end

% For Water Hazard

if (strcmp(LC_50{i},'NA') == 0)

if (0.1 < LC_50{i}) && (LC_50{i} < 1e3)

IndVal(i,3) = - 0.087*log(LC_50{i}) + 0.8;

elseif LC_50{i} <= 0.1

IndVal(i,3) = 1;

elseif LC_50{i} >= 1e3

IndVal(i,3) = 0;

end

elseif (strcmp(R_code{i},'NA') == 0)

if (R_code{i} == 50)

IndVal(i,3) = 0.875;

elseif (R_code{i} == 51)

IndVal(i,3) = 0.625;

elseif (R_code{i} == 52)

IndVal(i,3) = 0.375;

else

IndVal(i,3) = 0;

end

elseif (strcmp(GWK{i},'NA') == 0)

if GWK{i} == 3

IndVal(i,3) = 0.875;

elseif GWK{i} == 2

IndVal(i,3) = 0.5;

elseif GWK{i} == 1

IndVal(i,3) = 0.125;

elseif (strcmp(GWK{i},'nwg') == 1)

IndVal(i,3) = 0;

end
end

if IndVal(i,3) > 0

PhysVal(i,3) = 10^(4*IndVal(i,3) + 1);

elseif IndVal(i,3) == 0;

PhysVal(i,3) = 0;

end

end

return
